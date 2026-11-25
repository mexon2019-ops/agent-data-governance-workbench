import os
import base64
import hashlib
import hmac
import json
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Float, String, Table, Text, UniqueConstraint,
    create_engine, select, func, delete, MetaData, and_, or_, cast
)
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy import inspect as sa_inspect
from .agent_service import run_governance_agent
from .classification_service import suggest_field_classification
from .finereport_service import extract_sql_table_references

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


user_roles = Table("user_roles", Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True))
role_permissions = Table("role_permissions", Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True))
class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, back_populates="roles")
    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    roles: Mapped[list[Role]] = relationship(secondary=role_permissions, back_populates="permissions")
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="anonymous", index=True)
    action: Mapped[str] = mapped_column(String(20), index=True)
    resource: Mapped[str] = mapped_column(String(255), default="")
    http_method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Record(Base):
    __tablename__ = "governance_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="草稿")
    owner: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    db_type: Mapped[str] = mapped_column(String(30))
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    database: Mapped[str] = mapped_column(String(180))
    username: Mapped[str] = mapped_column(String(120))
    password_env_key: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="待测试")
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetadataTable(Base):
    __tablename__ = "metadata_tables"
    __table_args__ = (UniqueConstraint("source_id", "schema_name", "table_name", name="uq_metadata_table"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    schema_name: Mapped[str] = mapped_column(String(180), default="")
    table_name: Mapped[str] = mapped_column(String(180))
    table_type: Mapped[str] = mapped_column(String(30), default="TABLE")
    description: Mapped[str] = mapped_column(Text, default="")
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    columns: Mapped[list["MetadataColumn"]] = relationship(
        back_populates="table", cascade="all, delete-orphan", order_by="MetadataColumn.ordinal_position"
    )


class MetadataColumn(Base):
    __tablename__ = "metadata_columns"
    __table_args__ = (UniqueConstraint("table_id", "column_name", name="uq_metadata_column"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("metadata_tables.id", ondelete="CASCADE"), index=True)
    column_name: Mapped[str] = mapped_column(String(180))
    data_type: Mapped[str] = mapped_column(String(255), default="")
    nullable: Mapped[bool] = mapped_column(Boolean, default=True)
    default_value: Mapped[str] = mapped_column(Text, default="")
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_foreign_key: Mapped[bool] = mapped_column(Boolean, default=False)
    sensitivity_level: Mapped[str] = mapped_column(String(30), default="未分级")
    classification_basis: Mapped[str] = mapped_column(Text, default="")
    classified_by: Mapped[str] = mapped_column(String(80), default="")
    classified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    table: Mapped[MetadataTable] = relationship(back_populates="columns")


class MetadataLineage(Base):
    __tablename__ = "metadata_lineage"
    __table_args__ = (UniqueConstraint(
        "source_column_id", "target_schema_name", "target_table_name", "target_column_name",
        name="uq_metadata_lineage_edge",
    ),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_table_id: Mapped[int] = mapped_column(ForeignKey("metadata_tables.id", ondelete="CASCADE"), index=True)
    source_column_id: Mapped[int] = mapped_column(ForeignKey("metadata_columns.id", ondelete="CASCADE"), index=True)
    target_schema_name: Mapped[str] = mapped_column(String(180), default="")
    target_table_name: Mapped[str] = mapped_column(String(180))
    target_column_name: Mapped[str] = mapped_column(String(180))
    relation_type: Mapped[str] = mapped_column(String(30), default="FOREIGN_KEY")
    discovery_method: Mapped[str] = mapped_column(String(40), default="DATABASE_CONSTRAINT")
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MetadataSyncRun(Base):
    __tablename__ = "metadata_sync_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="运行中")
    table_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class DataAsset(Base):
    __tablename__ = "data_assets"
    __table_args__ = (
        UniqueConstraint("asset_code", name="uq_data_asset_code"),
        UniqueConstraint("metadata_table_id", name="uq_data_asset_metadata_table"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    metadata_table_id: Mapped[int | None] = mapped_column(
        ForeignKey("metadata_tables.id", ondelete="SET NULL"), nullable=True
    )
    business_domain: Mapped[str] = mapped_column(String(80), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_department: Mapped[str] = mapped_column(String(120), default="")
    owner: Mapped[str] = mapped_column(String(100), default="")
    sensitivity_level: Mapped[str] = mapped_column(String(30), default="未分级")
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="待确认")
    tags: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DataStandard(Base):
    __tablename__ = "data_standards"
    __table_args__ = (UniqueConstraint("standard_code", name="uq_data_standard_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    business_domain: Mapped[str] = mapped_column(String(80), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_department: Mapped[str] = mapped_column(String(120), default="")
    owner: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(30), default="草稿")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    versions: Mapped[list["DataStandardVersion"]] = relationship(
        back_populates="standard", cascade="all, delete-orphan", order_by="DataStandardVersion.version_number"
    )


class DataStandardVersion(Base):
    __tablename__ = "data_standard_versions"
    __table_args__ = (UniqueConstraint("standard_id", "version_number", name="uq_standard_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_id: Mapped[int] = mapped_column(ForeignKey("data_standards.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    definition: Mapped[str] = mapped_column(Text, default="")
    data_type: Mapped[str] = mapped_column(String(80), default="")
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    format_rule: Mapped[str] = mapped_column(String(500), default="")
    value_range: Mapped[str] = mapped_column(String(500), default="")
    example: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(30), default="草稿")
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    standard: Mapped[DataStandard] = relationship(back_populates="versions")
    mappings: Mapped[list["DataStandardMapping"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class DataStandardMapping(Base):
    __tablename__ = "data_standard_mappings"
    __table_args__ = (UniqueConstraint("version_id", "metadata_column_id", name="uq_standard_column_mapping"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("data_standard_versions.id", ondelete="CASCADE"), index=True)
    metadata_column_id: Mapped[int] = mapped_column(ForeignKey("metadata_columns.id", ondelete="CASCADE"), index=True)
    mapping_status: Mapped[str] = mapped_column(String(30), default="待核验")
    note: Mapped[str] = mapped_column(Text, default="")
    mapped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    version: Mapped[DataStandardVersion] = relationship(back_populates="mappings")

class QualityRule(Base):
    __tablename__ = "quality_rules"
    __table_args__ = (UniqueConstraint("rule_code", name="uq_quality_rule_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    metadata_table_id: Mapped[int] = mapped_column(ForeignKey("metadata_tables.id", ondelete="CASCADE"), index=True)
    metadata_column_id: Mapped[int] = mapped_column(ForeignKey("metadata_columns.id", ondelete="CASCADE"), index=True)
    standard_version_id: Mapped[int | None] = mapped_column(ForeignKey("data_standard_versions.id", ondelete="SET NULL"), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(30), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="中")
    threshold_rate: Mapped[float] = mapped_column(Float, default=100.0)
    config: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QualityRun(Base):
    __tablename__ = "quality_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("quality_rules.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="运行中")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class GovernanceIssue(Base):
    __tablename__ = "governance_issues"
    __table_args__ = (
        UniqueConstraint("issue_code", name="uq_governance_issue_code"),
        UniqueConstraint("quality_run_id", name="uq_governance_issue_quality_run"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_code: Mapped[str] = mapped_column(String(80), index=True)
    quality_run_id: Mapped[int | None] = mapped_column(ForeignKey("quality_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("quality_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="中")
    owner_department: Mapped[str] = mapped_column(String(120), default="")
    owner: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(30), default="待分派")
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remediation_note: Mapped[str] = mapped_column(Text, default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    last_recheck_run_id: Mapped[int | None] = mapped_column(ForeignKey("quality_runs.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)
class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern="^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(default="", max_length=120)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])

class RecordIn(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=180)
    description: str = ""
    status: str = "草稿"
    owner: str = ""


class DataSourceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    db_type: str = Field(pattern="^(sqlserver|oracle|mysql|postgresql)$")
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    database: str = Field(min_length=1, max_length=180)
    username: str = Field(min_length=1, max_length=120)
    password_env_key: str = Field(min_length=1, max_length=120, pattern="^[A-Z][A-Z0-9_]*$")
    description: str = ""



class FineReportImportIn(BaseModel):
    reports: list[dict[str, Any]] = Field(min_length=1, max_length=5000)

class LineageApprovalIn(BaseModel):
    report_id: str = Field(min_length=1, max_length=180)
    dataset: str = Field(min_length=1, max_length=180)
    table_ids: list[int] = Field(min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)

class AgentPrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    allow_external_model: bool = False

class MetadataColumnClassificationIn(BaseModel):
    sensitivity_level: str = Field(pattern="^(未分级|公开|内部|敏感|高度敏感)$")
    classification_basis: str = Field(default="", max_length=1000)

class DataAssetIn(BaseModel):
    asset_code: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=180)
    metadata_table_id: int | None = None
    business_domain: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=4000)
    owner_department: str = Field(default="", max_length=120)
    owner: str = Field(default="", max_length=100)
    sensitivity_level: str = Field(default="未分级", pattern="^(未分级|公开|内部|敏感|高度敏感)$")
    lifecycle_status: str = Field(default="待确认", pattern="^(待确认|建设中|已发布|已下线)$")
    tags: list[str] = Field(default_factory=list, max_length=30)

class DataStandardIn(BaseModel):
    standard_code: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=180)
    business_domain: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=4000)
    owner_department: str = Field(default="", max_length=120)
    owner: str = Field(default="", max_length=100)
    definition: str = Field(default="", max_length=4000)
    data_type: str = Field(default="", max_length=80)
    max_length: int | None = Field(default=None, ge=1, le=100000)
    required: bool = False
    format_rule: str = Field(default="", max_length=500)
    value_range: str = Field(default="", max_length=500)
    example: str = Field(default="", max_length=500)


class DataStandardVersionIn(BaseModel):
    definition: str = Field(default="", max_length=4000)
    data_type: str = Field(default="", max_length=80)
    max_length: int | None = Field(default=None, ge=1, le=100000)
    required: bool = False
    format_rule: str = Field(default="", max_length=500)
    value_range: str = Field(default="", max_length=500)
    example: str = Field(default="", max_length=500)


class DataStandardMappingIn(BaseModel):
    metadata_column_id: int
    mapping_status: str = Field(default="待核验", pattern="^(待核验|已落标|不符合)$")
    note: str = Field(default="", max_length=2000)

class QualityRuleIn(BaseModel):
    rule_code: str = Field(min_length=1, max_length=80, pattern="^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=180)
    metadata_table_id: int
    metadata_column_id: int
    standard_version_id: int | None = None
    rule_type: str = Field(pattern="^(completeness|uniqueness|range|enum)$")
    severity: str = Field(default="中", pattern="^(低|中|高)$")
    threshold_rate: float = Field(default=100.0, ge=0, le=100)
    config: dict[str, Any] = Field(default_factory=dict)

class GovernanceIssueCreateIn(BaseModel):
    quality_run_id: int
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=4000)
    severity: str = Field(default="中", pattern="^(低|中|高)$")
    owner_department: str = Field(default="", max_length=120)
    owner: str = Field(default="", max_length=100)
    due_date: datetime | None = None


class GovernanceIssueAssignIn(BaseModel):
    owner_department: str = Field(min_length=1, max_length=120)
    owner: str = Field(min_length=1, max_length=100)
    due_date: datetime | None = None


class GovernanceIssueRemediationIn(BaseModel):
    remediation_note: str = Field(min_length=1, max_length=4000)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "28800"))

def _auth_secret() -> bytes:
    secret = os.getenv("AUTH_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("AUTH_SECRET must be configured with at least 32 characters")
    return secret.encode("utf-8")

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return "pbkdf2_sha256$310000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256": return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def issue_token(user: User) -> str:
    now = int(time.time())
    payload = {"sub": str(user.id), "username": user.username, "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_auth_secret(), body.encode(), hashlib.sha256).digest()
    return body + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")

def decode_token(token: str) -> dict[str, Any] | None:
    try:
        body, supplied = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(_auth_secret(), body.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(expected, supplied): return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return payload if int(payload["exp"]) > int(time.time()) else None
    except Exception:
        return None

def user_public(user: User) -> dict[str, Any]:
    return {"id": user.id, "username": user.username, "display_name": user.display_name,
            "is_active": user.is_active, "roles": [r.name for r in user.roles],
            "permissions": sorted({p.code for r in user.roles for p in r.permissions})}

def current_user(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(db_session)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "请先登录")
    payload = decode_token(authorization[7:])
    if not payload: raise HTTPException(401, "登录凭证无效或已过期")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active: raise HTTPException(401, "用户不存在或已停用")
    request.state.actor = user.username
    return user

def require_permission(code: str):
    def checker(user: User = Depends(current_user)) -> User:
        permissions = {p.code for role in user.roles for p in role.permissions}
        if code not in permissions and "system:admin" not in permissions:
            raise HTTPException(403, "无权执行此操作")
        return user
    return checker

def bootstrap_auth(db: Session) -> None:
    permission_defs = {"user:manage":"管理用户和角色", "governance:read":"查看治理数据", "governance:write":"维护治理数据", "datasource:manage":"管理数据源", "audit:read":"查看操作审计"}
    perms = {}
    for code, desc in permission_defs.items():
        item = db.scalar(select(Permission).where(Permission.code == code))
        if item is None: item = Permission(code=code, description=desc); db.add(item)
        perms[code] = item
    defs = {"admin":("系统管理员",list(permission_defs)), "data_steward":("数据管理员",["governance:read","governance:write","datasource:manage"]), "auditor":("审计员",["governance:read","audit:read"]), "viewer":("只读用户",["governance:read"])}
    for name, pair in defs.items():
        desc, codes = pair
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None: role = Role(name=name, description=desc); db.add(role)
        role.permissions = [perms[x] for x in codes]
    db.flush()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if password:
        if len(password) < 16: raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must contain at least 16 characters")
        admin = db.scalar(select(User).where(User.username == "admin"))
        if admin is None:
            admin = User(username="admin", password_hash=hash_password(password), display_name="系统管理员", roles=[db.scalar(select(Role).where(Role.name == "admin"))])
            db.add(admin)
    db.commit()

def ensure_mysql_test_datasource(db: Session) -> DataSource | None:
    """Idempotently register the bundled Docker MySQL fixture when explicitly enabled."""
    if os.getenv("AUTO_REGISTER_MYSQL_TEST_DATASOURCE", "").lower() not in {"1", "true", "yes"}:
        return None
    name = "MySQL 测试数据库（mes_test）"
    row = db.scalar(select(DataSource).where(DataSource.name == name))
    if row is not None:
        return row
    row = DataSource(
        name=name,
        db_type="mysql",
        host=os.getenv("MYSQL_TEST_HOST", "mysql-test"),
        port=int(os.getenv("MYSQL_TEST_PORT", "3306")),
        database=os.getenv("MYSQL_TEST_DATABASE", "mes_test"),
        username=os.getenv("MYSQL_TEST_USERNAME", "metadata_reader"),
        password_env_key="MYSQL_TEST_READER_PASSWORD",
        description="项目自带的虚构 LED 制造场景测试库；只读账号，仅用于元数据采集验证。",
        status="待测试",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as auth_db:
        bootstrap_auth(auth_db)
    if os.getenv("AUTO_REGISTER_MYSQL_TEST_DATASOURCE", "").lower() in {"1", "true", "yes"}:
        with SessionLocal() as db:
            ensure_mysql_test_datasource(db)
    yield


app = FastAPI(title="Agent 数据治理工作台 API", version="0.3.0", lifespan=lifespan)
allowed_origins = [origin.strip() for origin in os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173"
).split(",") if origin.strip()]
@app.middleware("http")
async def audit_mutating_requests(request: Request, call_next):
    """Record API mutations without capturing request bodies, credentials, or query values."""
    request_id = str(uuid4())
    request.state.actor = "anonymous"
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token_payload = decode_token(auth_header[7:])
        if token_payload:
            with SessionLocal() as identity_db:
                identity = identity_db.get(User, int(token_payload["sub"]))
                if identity and identity.is_active:
                    request.state.actor = identity.username
    # Enforce authentication for every API except login. Health checks and CORS
    # preflight requests remain public. Admin endpoints perform their own RBAC checks.
    if request.url.path.startswith("/api/v1/") and request.url.path != "/api/v1/auth/login" and request.method != "OPTIONS":
        if request.state.actor == "anonymous":
            return JSONResponse(status_code=401, content={"detail": "请先登录"},
                                headers={"X-Request-ID": request_id})
        if not request.url.path.startswith("/api/v1/admin/") and request.url.path != "/api/v1/auth/me":
            required = "governance:read"
            path = request.url.path
            method = request.method
            if path.startswith("/api/v1/datasources"):
                required = "datasource:manage"
            elif (path.startswith("/api/v1/records") and method in {"POST", "PUT", "PATCH", "DELETE"}) :
                required = "governance:write"
            elif path == "/api/v1/agents/run":
                required = "governance:read"
            elif path.startswith("/api/v1/datasources/") and (path.endswith("/test") or path.endswith("/sync")):
                required = "datasource:manage"
            with SessionLocal() as permission_db:
                identity = permission_db.scalar(select(User).where(User.username == request.state.actor))
                permissions = {p.code for role in identity.roles for p in role.permissions} if identity else set()
            if required not in permissions:
                return JSONResponse(status_code=403, content={"detail": "无权执行此操作"},
                                    headers={"X-Request-ID": request_id})
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        # Authentication is not yet wired in this sprint. Never trust a caller-
        # supplied identity header; use an explicit anonymous placeholder.
        with SessionLocal() as audit_db:
            audit_db.add(AuditLog(
                request_id=request_id,
                actor=getattr(request.state, "actor", "anonymous"),
                action=request.method,
                resource=request.url.path[:255],
                http_method=request.method,
                path=request.url.path[:500],
                status_code=locals().get("status_code", 500),
            ))
            audit_db.commit()

    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.post("/api/v1/auth/login")
def login(payload: LoginIn, db: Session = Depends(db_session)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return {"access_token": issue_token(user), "token_type": "bearer", "expires_in": TOKEN_TTL_SECONDS, "user": user_public(user)}

@app.get("/api/v1/auth/me")
def auth_me(user: User = Depends(current_user)):
    return user_public(user)

@app.get("/api/v1/admin/users")
def list_users(_admin: User = Depends(require_permission("user:manage")), db: Session = Depends(db_session)):
    return [user_public(user) for user in db.scalars(select(User).order_by(User.id)).all()]

@app.post("/api/v1/admin/users", status_code=201)
def create_user(payload: UserCreateIn, _admin: User = Depends(require_permission("user:manage")), db: Session = Depends(db_session)):
    if db.scalar(select(User).where(User.username == payload.username)): raise HTTPException(409, "用户名已存在")
    roles = db.scalars(select(Role).where(Role.name.in_(payload.roles))).all()
    if len(roles) != len(set(payload.roles)): raise HTTPException(400, "包含不存在的角色")
    user = User(username=payload.username, password_hash=hash_password(payload.password), display_name=payload.display_name, is_active=True, roles=roles)
    db.add(user); db.commit(); db.refresh(user)
    return user_public(user)

@app.get("/api/v1/admin/roles")
def list_roles(_admin: User = Depends(require_permission("user:manage")), db: Session = Depends(db_session)):
    return [{"name": role.name, "description": role.description, "permissions": sorted(p.code for p in role.permissions)} for role in db.scalars(select(Role).order_by(Role.id)).all()]

@app.get("/api/v1/admin/audit-logs")
def list_audit_logs(
    _admin: User = Depends(require_permission("audit:read")),
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(db_session),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).offset(offset).limit(limit)).all()
    return [{
        "id": row.id, "request_id": row.request_id, "actor": row.actor,
        "action": row.action, "resource": row.resource,
        "http_method": row.http_method, "path": row.path,
        "status_code": row.status_code, "created_at": row.created_at,
    } for row in rows]

@app.get("/health")
def health():
    return {"status": "ok", "service": "data-governance-api", "version": "0.3.0"}


@app.get("/api/v1/dashboard")
def dashboard(db: Session = Depends(db_session)):
    counts = {c: db.scalar(select(func.count()).select_from(Record).where(Record.category == c)) or 0
              for c in ["quality", "task"]}
    counts["asset"] = db.scalar(select(func.count()).select_from(DataAsset)) or 0
    counts["standard"] = db.scalar(select(func.count()).select_from(DataStandard)) or 0
    counts["quality"] = db.scalar(select(func.count()).select_from(QualityRule)) or 0
    counts["data_sources"] = db.scalar(select(func.count()).select_from(DataSource)) or 0
    counts["metadata_tables"] = db.scalar(select(func.count()).select_from(MetadataTable)) or 0
    counts["metadata_columns"] = db.scalar(select(func.count()).select_from(MetadataColumn)) or 0
    counts["pending_tasks"] = db.scalar(select(func.count()).select_from(GovernanceIssue).where(
        GovernanceIssue.status != "已关闭")) or 0
    return counts



@app.post("/api/v1/finereport/reports/import", status_code=200)
def import_finereport_inventory(
    payload: FineReportImportIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    """Import read-only inventory export. Records are stored as JSON in governance Records."""
    imported = 0
    for report in payload.reports:
        report_id = str(report.get("report_id") or report.get("id") or "").strip()
        name = str(report.get("name") or report.get("report_name") or "").strip()
        if not report_id or not name:
            raise HTTPException(422, "每个报表必须包含 report_id/id 和 name/report_name")
        safe = {k: report.get(k) for k in ("report_id", "id", "name", "report_name", "folder", "path", "owner", "datasets", "dataset_sql", "datasource") if k in report}
        safe["report_id"] = report_id
        safe["name"] = name
        serialized = json.dumps(safe, ensure_ascii=False)
        existing = db.scalar(select(Record).where(Record.category == "finereport_report", Record.name == report_id))
        if existing:
            existing.description = serialized
            existing.status = "已导入"
            existing.owner = str(report.get("owner") or "")
        else:
            db.add(Record(category="finereport_report", name=report_id, description=serialized, status="已导入", owner=str(report.get("owner") or "")))
        imported += 1
    db.commit()
    return {"success": True, "imported": imported, "category": "finereport_report"}

@app.get("/api/v1/finereport/reports")
def list_finereport_inventory(db: Session = Depends(db_session)):
    rows = db.scalars(select(Record).where(Record.category == "finereport_report").order_by(Record.id.desc())).all()
    results = []
    for row in rows:
        try:
            data = json.loads(row.description or "{}")
        except (TypeError, json.JSONDecodeError):
            data = {}
        results.append({"id": row.id, "report_id": row.name, "status": row.status, "owner": row.owner, **data})
    return results



@app.get("/api/v1/finereport/reports/{report_id}/lineage-approved")
def get_approved_report_lineage(report_id: str, _user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    rows = db.scalars(select(Record).where(Record.category == "finereport_lineage_approved", Record.name == report_id).order_by(Record.id.desc())).all()
    return [{"id": row.id, "report_id": row.name, "status": row.status, **(json.loads(row.description or "{}"))} for row in rows]


@app.post("/api/v1/finereport/lineage/approve")
def approve_report_lineage(payload: LineageApprovalIn, _user: User = Depends(require_permission("governance:write")), db: Session = Depends(db_session)):
    report = db.scalar(select(Record).where(Record.category == "finereport_report", Record.name == payload.report_id))
    if not report:
        raise HTTPException(404, "FineReport报表不存在")
    unique_ids = list(dict.fromkeys(payload.table_ids))
    tables = db.scalars(select(MetadataTable).where(MetadataTable.id.in_(unique_ids))).all()
    if len(tables) != len(unique_ids):
        raise HTTPException(400, "包含不存在的元数据表ID")
    approved = {"dataset": payload.dataset, "table_ids": unique_ids,
                "tables": [{"table_id": t.id, "source_id": t.source_id, "schema_name": t.schema_name, "table_name": t.table_name} for t in tables],
                "notes": payload.notes, "approved_by": _user.username, "approved_at": datetime.utcnow().isoformat()}
    row = Record(category="finereport_lineage_approved", name=payload.report_id,
                 description=json.dumps(approved, ensure_ascii=False), status="已确认", owner=_user.username)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status, **approved}

@app.get("/api/v1/records")
def list_records(category: str | None = None, db: Session = Depends(db_session)):
    stmt = select(Record).order_by(Record.id.desc())
    if category:
        stmt = stmt.where(Record.category == category)
    return db.scalars(stmt).all()


@app.post("/api/v1/records", status_code=201)
def create_record(payload: RecordIn, db: Session = Depends(db_session)):
    row = Record(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.patch("/api/v1/records/{record_id}")
def update_record(record_id: int, payload: dict, db: Session = Depends(db_session)):
    row = db.get(Record, record_id)
    if not row:
        raise HTTPException(404, "记录不存在")
    for key, value in payload.items():
        if key in {"category", "name", "description", "status", "owner"}:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/api/v1/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(db_session)):
    row = db.get(Record, record_id)
    if not row:
        raise HTTPException(404, "记录不存在")
    db.delete(row)
    db.commit()


def datasource_public(row: DataSource):
    return {k: getattr(row, k) for k in ["id", "name", "db_type", "host", "port", "database",
            "username", "password_env_key", "description", "status", "last_test_at", "created_at"]}


def build_source_engine(row: DataSource):
    password = os.getenv(row.password_env_key)
    if not password:
        raise ValueError(f"服务端未配置环境变量 {row.password_env_key}；密码不会存入数据库")
    drivers = {
        "sqlserver": ("mssql+pymssql", {"login_timeout": 8, "timeout": 15}),
        "oracle": ("oracle+oracledb", {"tcp_connect_timeout": 8}),
        "mysql": ("mysql+pymysql", {"connect_timeout": 8, "read_timeout": 30, "write_timeout": 30}),
        "postgresql": ("postgresql+psycopg", {"connect_timeout": 8}),
    }
    dialect, connect_args = drivers[row.db_type]
    url = URL.create(dialect, username=row.username, password=password, host=row.host,
                     port=row.port, database=row.database)
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


@app.get("/api/v1/datasources")
def list_datasources(db: Session = Depends(db_session)):
    return [datasource_public(x) for x in db.scalars(select(DataSource).order_by(DataSource.id.desc())).all()]


@app.post("/api/v1/datasources", status_code=201)
def create_datasource(payload: DataSourceIn, db: Session = Depends(db_session)):
    if db.scalar(select(DataSource).where(DataSource.name == payload.name)):
        raise HTTPException(409, "数据源名称已存在")
    row = DataSource(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return datasource_public(row)


@app.patch("/api/v1/datasources/{source_id}")
def update_datasource(source_id: int, payload: DataSourceIn, db: Session = Depends(db_session)):
    row = db.get(DataSource, source_id)
    if not row:
        raise HTTPException(404, "数据源不存在")
    if payload.name != row.name and db.scalar(select(DataSource).where(DataSource.name == payload.name)):
        raise HTTPException(409, "数据源名称已存在")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.status = "待测试"
    db.commit()
    db.refresh(row)
    return datasource_public(row)


@app.delete("/api/v1/datasources/{source_id}", status_code=204)
def delete_datasource(source_id: int, db: Session = Depends(db_session)):
    row = db.get(DataSource, source_id)
    if not row:
        raise HTTPException(404, "数据源不存在")
    db.delete(row)
    db.commit()


@app.post("/api/v1/datasources/{source_id}/test")
def test_datasource(source_id: int, db: Session = Depends(db_session)):
    row = db.get(DataSource, source_id)
    if not row:
        raise HTTPException(404, "数据源不存在")
    test_engine = None
    try:
        test_engine = build_source_engine(row)
        with test_engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        row.status = "连接成功"
        result = {"success": True, "message": "连接成功"}
    except ValueError as exc:
        row.status = "待配置凭据"
        result = {"success": False, "message": str(exc)}
    except Exception as exc:
        row.status = "连接失败"
        result = {"success": False, "message": f"连接失败：{type(exc).__name__}，请检查网络、驱动和凭据配置"}
    finally:
        if test_engine is not None:
            test_engine.dispose()
    row.last_test_at = datetime.utcnow()
    db.commit()
    return result


def table_public(row: MetadataTable, source_name: str | None = None):
    result = {k: getattr(row, k) for k in ["id", "source_id", "schema_name", "table_name",
              "table_type", "description", "column_count", "synced_at"]}
    if source_name is not None:
        result["source_name"] = source_name
    return result


@app.get("/api/v1/metadata/tables")
def list_metadata_tables(source_id: int | None = None, keyword: str | None = None,
                         db: Session = Depends(db_session)):
    stmt = select(MetadataTable, DataSource.name).join(DataSource, MetadataTable.source_id == DataSource.id)
    if source_id:
        stmt = stmt.where(MetadataTable.source_id == source_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((MetadataTable.table_name.ilike(like)) |
                          (MetadataTable.schema_name.ilike(like)) |
                          (MetadataTable.description.ilike(like)))
    stmt = stmt.order_by(DataSource.name, MetadataTable.schema_name, MetadataTable.table_name)
    return [table_public(row, source_name) for row, source_name in db.execute(stmt).all()]


@app.get("/api/v1/metadata/tables/{table_id}")
def get_metadata_table(table_id: int, db: Session = Depends(db_session)):
    row = db.get(MetadataTable, table_id)
    if not row:
        raise HTTPException(404, "元数据表不存在")
    source = db.get(DataSource, row.source_id)
    columns = []
    for column in row.columns:
        mappings = db.execute(
            select(DataStandardMapping, DataStandardVersion, DataStandard)
            .join(DataStandardVersion, DataStandardMapping.version_id == DataStandardVersion.id)
            .join(DataStandard, DataStandardVersion.standard_id == DataStandard.id)
            .where(DataStandardMapping.metadata_column_id == column.id)
        ).all()
        columns.append({
            "id": column.id, "column_name": column.column_name, "data_type": column.data_type,
            "nullable": column.nullable, "default_value": column.default_value,
            "ordinal_position": column.ordinal_position, "description": column.description,
            "is_primary_key": column.is_primary_key, "is_foreign_key": column.is_foreign_key,
            "sensitivity_level": column.sensitivity_level,
            "classification_basis": column.classification_basis,
            "classified_by": column.classified_by,
            "classified_at": column.classified_at,
            "standard_mappings": [{
                "mapping_id": mapping.id, "standard_id": standard.id,
                "standard_code": standard.standard_code, "standard_name": standard.name,
                "version_id": version.id, "version_number": version.version_number,
                "mapping_status": mapping.mapping_status, "note": mapping.note,
            } for mapping, version, standard in mappings],
        })
    return {
        **table_public(row, source.name if source else ""),
        "columns": columns,
    }


@app.get("/api/v1/metadata/columns/{column_id}/classification-suggestion")
def get_metadata_column_classification_suggestion(column_id: int, db: Session = Depends(db_session)):
    column = db.get(MetadataColumn, column_id)
    if not column:
        raise HTTPException(404, "元数据字段不存在")
    return suggest_field_classification(column.column_name, column.data_type)


@app.patch("/api/v1/metadata/columns/{column_id}/classification")
def classify_metadata_column(
    column_id: int,
    payload: MetadataColumnClassificationIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    column = db.get(MetadataColumn, column_id)
    if not column:
        raise HTTPException(404, "元数据字段不存在")
    column.sensitivity_level = payload.sensitivity_level
    column.classification_basis = payload.classification_basis.strip()
    column.classified_by = _user.username
    column.classified_at = datetime.utcnow()
    db.commit()
    db.refresh(column)
    return {
        "id": column.id,
        "sensitivity_level": column.sensitivity_level,
        "classification_basis": column.classification_basis,
        "classified_by": column.classified_by,
        "classified_at": column.classified_at,
    }


@app.get("/api/v1/metadata/lineage")
def list_metadata_lineage(
    source_id: int | None = None,
    table_id: int | None = None,
    db: Session = Depends(db_session),
):
    stmt = (
        select(MetadataLineage, MetadataTable, MetadataColumn, DataSource.name)
        .join(MetadataTable, MetadataLineage.source_table_id == MetadataTable.id)
        .join(MetadataColumn, MetadataLineage.source_column_id == MetadataColumn.id)
        .join(DataSource, MetadataTable.source_id == DataSource.id)
    )
    if source_id is not None:
        stmt = stmt.where(MetadataTable.source_id == source_id)
    if table_id is not None:
        stmt = stmt.where(MetadataTable.id == table_id)
    rows = db.execute(stmt.order_by(
        DataSource.name, MetadataTable.schema_name, MetadataTable.table_name,
        MetadataColumn.column_name,
    )).all()
    return [{
        "id": edge.id,
        "source_table_id": table.id,
        "source_column_id": column.id,
        "source_id": table.source_id,
        "source_name": source_name,
        "source_schema": table.schema_name,
        "source_table": table.table_name,
        "source_column": column.column_name,
        "target_schema": edge.target_schema_name,
        "target_table": edge.target_table_name,
        "target_column": edge.target_column_name,
        "relation_type": edge.relation_type,
        "discovery_method": edge.discovery_method,
        "discovered_at": edge.discovered_at,
    } for edge, table, column, source_name in rows]


@app.get("/api/v1/datasources/{source_id}/sync-runs")
def list_sync_runs(source_id: int, db: Session = Depends(db_session)):
    if not db.get(DataSource, source_id):
        raise HTTPException(404, "数据源不存在")
    rows = db.scalars(select(MetadataSyncRun).where(
        MetadataSyncRun.source_id == source_id).order_by(MetadataSyncRun.id.desc()).limit(20)).all()
    return rows


@app.post("/api/v1/datasources/{source_id}/sync")
def sync_metadata(source_id: int, db: Session = Depends(db_session)):
    source = db.get(DataSource, source_id)
    if not source:
        raise HTTPException(404, "数据源不存在")
    run = MetadataSyncRun(source_id=source_id, status="运行中", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)
    source_engine = None
    try:
        source_engine = build_source_engine(source)
        inspector = sa_inspect(source_engine)
        # MySQL exposes multiple databases as schemas. Restrict collection to the
        # database explicitly configured for this datasource to avoid catalog sprawl.
        if source.db_type == "mysql":
            schemas = [source.database]
        else:
            schemas = inspector.get_schema_names()
            excluded = {"information_schema", "performance_schema", "mysql", "sys",
                        "pg_catalog", "pg_toast", "sysaux", "system", "xdb"}
            schemas = [s for s in schemas if s.lower() not in excluded]
            if not schemas:
                schemas = [None]
        discovered: set[tuple[str, str]] = set()
        table_count = 0
        column_count = 0
        for schema in schemas:
            schema_name = schema or ""
            try:
                table_names = inspector.get_table_names(schema=schema)
                view_names = inspector.get_view_names(schema=schema)
            except Exception as exc:
                raise RuntimeError(f"无法读取数据库 {schema_name or source.database} 的表目录：{type(exc).__name__}") from exc
            for table_name in sorted(set(table_names + view_names)):
                key = (schema_name, table_name)
                discovered.add(key)
                is_view = table_name in view_names
                try:
                    columns = inspector.get_columns(table_name, schema=schema)
                except Exception:
                    continue
                try:
                    pk_cols = set((inspector.get_pk_constraint(table_name, schema=schema) or {}).get("constrained_columns") or [])
                except Exception:
                    pk_cols = set()
                try:
                    foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
                except Exception:
                    foreign_keys = []
                fk_relations = []
                for fk in foreign_keys:
                    source_columns = fk.get("constrained_columns") or []
                    target_columns = fk.get("referred_columns") or []
                    target_table = str(fk.get("referred_table") or "")
                    target_schema = str(fk.get("referred_schema") or schema_name)
                    for source_column, target_column in zip(source_columns, target_columns):
                        fk_relations.append((
                            str(source_column), target_schema, target_table, str(target_column)
                        ))
                fk_cols = {item[0] for item in fk_relations}
                try:
                    comment = (inspector.get_table_comment(table_name, schema=schema) or {}).get("text") or ""
                except Exception:
                    comment = ""
                existing = db.scalar(select(MetadataTable).where(
                    MetadataTable.source_id == source_id,
                    MetadataTable.schema_name == schema_name,
                    MetadataTable.table_name == table_name))
                if existing is None:
                    existing = MetadataTable(source_id=source_id, schema_name=schema_name, table_name=table_name)
                    db.add(existing)
                    db.flush()
                existing.table_type = "VIEW" if is_view else "TABLE"
                existing.description = str(comment)[:4000]
                existing.column_count = len(columns)
                existing.synced_at = datetime.utcnow()
                # Upsert columns by physical name so metadata IDs remain stable across
                # repeatable syncs; standards/quality mappings reference these IDs.
                db.execute(delete(MetadataLineage).where(
                    MetadataLineage.source_table_id == existing.id,
                    MetadataLineage.discovery_method == "DATABASE_CONSTRAINT",
                ))
                old_columns = {item.column_name: item for item in existing.columns}
                seen_columns: set[str] = set()
                for index, col in enumerate(columns, start=1):
                    column_name = str(col.get("name", ""))
                    if not column_name:
                        continue
                    seen_columns.add(column_name)
                    default = col.get("default")
                    column_row = old_columns.get(column_name)
                    if column_row is None:
                        column_row = MetadataColumn(column_name=column_name)
                        existing.columns.append(column_row)
                    column_row.data_type = str(col.get("type", ""))[:255]
                    column_row.nullable = bool(col.get("nullable", True))
                    column_row.default_value = "" if default is None else str(default)[:1000]
                    column_row.ordinal_position = int(col.get("ordinal") or index)
                    column_row.description = str(col.get("comment") or "")[:4000]
                    column_row.is_primary_key = column_name in pk_cols
                    column_row.is_foreign_key = column_name in fk_cols
                for old_name, old_column in old_columns.items():
                    if old_name not in seen_columns:
                        db.delete(old_column)
                db.flush()
                for source_column_name, target_schema, target_table, target_column in fk_relations:
                    source_column = db.scalar(select(MetadataColumn).where(
                        MetadataColumn.table_id == existing.id,
                        MetadataColumn.column_name == source_column_name,
                    ))
                    if source_column and target_table and target_column:
                        db.add(MetadataLineage(
                            source_table_id=existing.id,
                            source_column_id=source_column.id,
                            target_schema_name=target_schema,
                            target_table_name=target_table,
                            target_column_name=target_column,
                            relation_type="FOREIGN_KEY",
                            discovery_method="DATABASE_CONSTRAINT",
                        ))
                table_count += 1
                column_count += len(columns)
        stale = db.scalars(select(MetadataTable).where(MetadataTable.source_id == source_id)).all()
        for old in stale:
            if (old.schema_name, old.table_name) not in discovered:
                db.execute(delete(MetadataLineage).where(
                    MetadataLineage.source_table_id == old.id
                ))
                db.delete(old)
        run.status = "成功"
        run.table_count = table_count
        run.column_count = column_count
        run.message = "仅采集数据库结构元数据，未读取业务表数据行。"
        run.finished_at = datetime.utcnow()
        source.status = "采集成功"
        db.commit()
        return {"success": True, "run_id": run.id, "table_count": table_count,
                "column_count": column_count, "message": run.message}
    except ValueError as exc:
        db.rollback()
        run = db.get(MetadataSyncRun, run.id)
        run.status = "失败"
        run.message = str(exc)
        run.finished_at = datetime.utcnow()
        failed_source = db.get(DataSource, source_id)
        if failed_source:
            failed_source.status = "待配置凭据"
        db.commit()
        return {"success": False, "run_id": run.id, "message": run.message}
    except Exception as exc:
        db.rollback()
        run = db.get(MetadataSyncRun, run.id)
        run.status = "失败"
        run.message = f"采集失败：{type(exc).__name__}。请检查网络、账号权限和数据库驱动。"
        run.finished_at = datetime.utcnow()
        failed_source = db.get(DataSource, source_id)
        if failed_source:
            failed_source.status = "采集失败"
        db.commit()
        return {"success": False, "run_id": run.id, "message": run.message}
    finally:
        if source_engine is not None:
            source_engine.dispose()



def asset_public(row: DataAsset, metadata: MetadataTable | None = None, source_name: str | None = None):
    return {
        "id": row.id, "asset_code": row.asset_code, "name": row.name,
        "metadata_table_id": row.metadata_table_id,
        "business_domain": row.business_domain, "description": row.description,
        "owner_department": row.owner_department, "owner": row.owner,
        "sensitivity_level": row.sensitivity_level, "lifecycle_status": row.lifecycle_status,
        "tags": [tag for tag in row.tags.split(",") if tag],
        "created_at": row.created_at, "updated_at": row.updated_at,
        "source_name": source_name or "",
        "schema_name": metadata.schema_name if metadata else "",
        "table_name": metadata.table_name if metadata else "",
    }


@app.get("/api/v1/assets")
def list_data_assets(
    keyword: str | None = None,
    business_domain: str | None = None,
    owner_department: str | None = None,
    lifecycle_status: str | None = None,
    db: Session = Depends(db_session),
):
    stmt = select(DataAsset, MetadataTable, DataSource.name).outerjoin(
        MetadataTable, DataAsset.metadata_table_id == MetadataTable.id
    ).outerjoin(DataSource, MetadataTable.source_id == DataSource.id)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            DataAsset.name.ilike(like) | DataAsset.asset_code.ilike(like) |
            DataAsset.description.ilike(like) | DataAsset.owner.ilike(like) |
            DataAsset.owner_department.ilike(like) | DataAsset.tags.ilike(like) |
            MetadataTable.table_name.ilike(like)
        )
    if business_domain:
        stmt = stmt.where(DataAsset.business_domain == business_domain)
    if owner_department:
        stmt = stmt.where(DataAsset.owner_department == owner_department)
    if lifecycle_status:
        stmt = stmt.where(DataAsset.lifecycle_status == lifecycle_status)
    stmt = stmt.order_by(DataAsset.updated_at.desc(), DataAsset.id.desc())
    return [asset_public(asset, metadata, source_name) for asset, metadata, source_name in db.execute(stmt).all()]


@app.post("/api/v1/assets", status_code=201)
def create_data_asset(
    payload: DataAssetIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    if db.scalar(select(DataAsset).where(DataAsset.asset_code == payload.asset_code)):
        raise HTTPException(409, "资产编码已存在")
    if payload.metadata_table_id is not None:
        if not db.get(MetadataTable, payload.metadata_table_id):
            raise HTTPException(404, "关联的元数据表不存在")
        if db.scalar(select(DataAsset).where(DataAsset.metadata_table_id == payload.metadata_table_id)):
            raise HTTPException(409, "该元数据表已登记为数据资产")
    values = payload.model_dump()
    values["tags"] = ",".join(dict.fromkeys(tag.strip() for tag in values["tags"] if tag.strip()))
    row = DataAsset(**values)
    db.add(row)
    db.commit()
    db.refresh(row)
    metadata = db.get(MetadataTable, row.metadata_table_id) if row.metadata_table_id else None
    source = db.get(DataSource, metadata.source_id) if metadata else None
    return asset_public(row, metadata, source.name if source else "")


@app.patch("/api/v1/assets/{asset_id}")
def update_data_asset(
    asset_id: int,
    payload: dict,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(DataAsset, asset_id)
    if not row:
        raise HTTPException(404, "数据资产不存在")
    allowed = {"name", "business_domain", "description", "owner_department", "owner",
               "sensitivity_level", "lifecycle_status", "tags"}
    for key, value in payload.items():
        if key not in allowed:
            continue
        if key == "tags":
            if not isinstance(value, list) or len(value) > 30 or any(not isinstance(x, str) for x in value):
                raise HTTPException(422, "tags 必须为最多 30 个字符串组成的数组")
            value = ",".join(dict.fromkeys(tag.strip() for tag in value if tag.strip()))
        if key == "sensitivity_level" and value not in {"未分级", "公开", "内部", "敏感", "高度敏感"}:
            raise HTTPException(422, "无效的敏感级别")
        if key == "lifecycle_status" and value not in {"待确认", "建设中", "已发布", "已下线"}:
            raise HTTPException(422, "无效的资产状态")
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    metadata = db.get(MetadataTable, row.metadata_table_id) if row.metadata_table_id else None
    return asset_public(row, metadata)


@app.delete("/api/v1/assets/{asset_id}", status_code=204)
def delete_data_asset(
    asset_id: int,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(DataAsset, asset_id)
    if not row:
        raise HTTPException(404, "数据资产不存在")
    db.delete(row)
    db.commit()



def standard_version_public(row: DataStandardVersion):
    return {
        "id": row.id, "standard_id": row.standard_id, "version_number": row.version_number,
        "definition": row.definition, "data_type": row.data_type, "max_length": row.max_length,
        "required": row.required, "format_rule": row.format_rule, "value_range": row.value_range,
        "example": row.example, "status": row.status, "effective_at": row.effective_at,
        "created_at": row.created_at,
    }


def standard_public(row: DataStandard, include_versions: bool = False):
    result = {
        "id": row.id, "standard_code": row.standard_code, "name": row.name,
        "business_domain": row.business_domain, "description": row.description,
        "owner_department": row.owner_department, "owner": row.owner,
        "status": row.status, "current_version": row.current_version,
        "created_at": row.created_at, "updated_at": row.updated_at,
    }
    if include_versions:
        result["versions"] = [standard_version_public(v) for v in row.versions]
    else:
        current = next((v for v in row.versions if v.version_number == row.current_version), None)
        result["current"] = standard_version_public(current) if current else None
    return result


@app.get("/api/v1/standards")
def list_data_standards(
    keyword: str | None = None,
    business_domain: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
):
    stmt = select(DataStandard).order_by(DataStandard.updated_at.desc(), DataStandard.id.desc())
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(DataStandard.standard_code.ilike(like) | DataStandard.name.ilike(like) |
                          DataStandard.description.ilike(like))
    if business_domain:
        stmt = stmt.where(DataStandard.business_domain == business_domain)
    if status:
        stmt = stmt.where(DataStandard.status == status)
    return [standard_public(row) for row in db.scalars(stmt).all()]


@app.get("/api/v1/standards/{standard_id}")
def get_data_standard(standard_id: int, db: Session = Depends(db_session)):
    row = db.get(DataStandard, standard_id)
    if not row:
        raise HTTPException(404, "数据标准不存在")
    result = standard_public(row, include_versions=True)
    mappings = []
    for version in row.versions:
        for mapping in version.mappings:
            column = db.get(MetadataColumn, mapping.metadata_column_id)
            table = db.get(MetadataTable, column.table_id) if column else None
            source = db.get(DataSource, table.source_id) if table else None
            mappings.append({
                "id": mapping.id, "version_id": mapping.version_id,
                "version_number": version.version_number,
                "metadata_column_id": mapping.metadata_column_id,
                "source_name": source.name if source else "",
                "schema_name": table.schema_name if table else "",
                "table_name": table.table_name if table else "",
                "column_name": column.column_name if column else "",
                "data_type": column.data_type if column else "",
                "mapping_status": mapping.mapping_status, "note": mapping.note,
                "mapped_at": mapping.mapped_at,
            })
    result["mappings"] = mappings
    return result


@app.post("/api/v1/standards", status_code=201)
def create_data_standard(
    payload: DataStandardIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    if db.scalar(select(DataStandard).where(DataStandard.standard_code == payload.standard_code)):
        raise HTTPException(409, "标准编码已存在")
    values = payload.model_dump()
    version_values = {key: values.pop(key) for key in [
        "definition", "data_type", "max_length", "required", "format_rule", "value_range", "example"
    ]}
    row = DataStandard(**values, current_version=1, status="草稿")
    row.versions.append(DataStandardVersion(version_number=1, status="草稿", **version_values))
    db.add(row)
    db.commit()
    db.refresh(row)
    return standard_public(row, include_versions=True)


@app.patch("/api/v1/standards/{standard_id}")
def update_data_standard(
    standard_id: int,
    payload: dict,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(DataStandard, standard_id)
    if not row:
        raise HTTPException(404, "数据标准不存在")
    for key in {"name", "business_domain", "description", "owner_department", "owner"}:
        if key in payload:
            setattr(row, key, str(payload[key])[:4000])
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return standard_public(row)


@app.post("/api/v1/standards/{standard_id}/versions", status_code=201)
def create_standard_version(
    standard_id: int,
    payload: DataStandardVersionIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(DataStandard, standard_id)
    if not row:
        raise HTTPException(404, "数据标准不存在")
    next_version = (db.scalar(select(func.max(DataStandardVersion.version_number)).where(
        DataStandardVersion.standard_id == standard_id)) or 0) + 1
    version = DataStandardVersion(standard_id=standard_id, version_number=next_version,
                                  status="草稿", **payload.model_dump())
    db.add(version)
    row.current_version = next_version
    row.status = "草稿"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(version)
    return standard_version_public(version)


@app.post("/api/v1/standards/{standard_id}/versions/{version_id}/publish")
def publish_standard_version(
    standard_id: int,
    version_id: int,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(DataStandard, standard_id)
    version = db.get(DataStandardVersion, version_id)
    if not row or not version or version.standard_id != standard_id:
        raise HTTPException(404, "标准或版本不存在")
    if version.version_number != row.current_version:
        raise HTTPException(409, "只能发布当前编辑版本")
    for old in row.versions:
        if old.id != version.id and old.status in {"已发布", "草稿"}:
            old.status = "已废止"
    version.status = "已发布"
    version.effective_at = datetime.utcnow()
    row.status = "已发布"
    row.updated_at = datetime.utcnow()
    db.commit()
    return standard_public(row, include_versions=True)


@app.post("/api/v1/standards/{standard_id}/versions/{version_id}/mappings", status_code=201)
def create_standard_mapping(
    standard_id: int,
    version_id: int,
    payload: DataStandardMappingIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    version = db.get(DataStandardVersion, version_id)
    if not version or version.standard_id != standard_id:
        raise HTTPException(404, "标准版本不存在")
    column = db.get(MetadataColumn, payload.metadata_column_id)
    if not column:
        raise HTTPException(404, "元数据字段不存在")
    existing = db.scalar(select(DataStandardMapping).where(
        DataStandardMapping.version_id == version_id,
        DataStandardMapping.metadata_column_id == payload.metadata_column_id,
    ))
    if existing:
        raise HTTPException(409, "该字段已映射到此标准版本")
    mapping = DataStandardMapping(version_id=version_id, **payload.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return {
        "id": mapping.id, "version_id": mapping.version_id,
        "metadata_column_id": mapping.metadata_column_id,
        "mapping_status": mapping.mapping_status, "note": mapping.note,
        "mapped_at": mapping.mapped_at,
    }



def quality_rule_public(row: QualityRule):
    return {
        "id": row.id, "rule_code": row.rule_code, "name": row.name,
        "metadata_table_id": row.metadata_table_id, "metadata_column_id": row.metadata_column_id,
        "standard_version_id": row.standard_version_id, "rule_type": row.rule_type,
        "severity": row.severity, "threshold_rate": row.threshold_rate,
        "config": json.loads(row.config or "{}"), "enabled": row.enabled,
        "created_at": row.created_at, "updated_at": row.updated_at,
    }


@app.get("/api/v1/governance/classification-suggestions")
def governance_classification_suggestions(limit: int = 500, db: Session = Depends(db_session)):
    """Metadata-only batch classification suggestions; never reads business rows."""
    from .classification_service import suggest_field_classification
    limit = max(1, min(limit, 2000))
    columns = db.scalars(select(MetadataColumn).order_by(MetadataColumn.id).limit(limit)).all()
    result = []
    for column in columns:
        table = db.get(MetadataTable, column.table_id)
        result.append({"column_id": column.id, "table_id": column.table_id,
            "schema_name": table.schema_name if table else "", "table_name": table.table_name if table else "",
            "column_name": column.column_name, "data_type": column.data_type,
            "current_level": column.sensitivity_level,
            "suggestion": suggest_field_classification(column.column_name, column.data_type)})
    return {"count": len(result), "limit": limit, "suggestions": result,
        "notice": "仅元数据字段名与类型推断建议，需人工审核；不读取业务数据行。"}

@app.get("/api/v1/governance/standard-rule-preview")
def governance_standard_rule_preview(db: Session = Depends(db_session)):
    """Preview rule candidates from approved mappings to published standards; no writes."""
    versions = db.scalars(select(DataStandardVersion).where(DataStandardVersion.status == "已发布")).all()
    candidates = []
    for version in versions:
        standard = db.get(DataStandard, version.standard_id)
        for mapping in version.mappings:
            if mapping.mapping_status not in {"已确认", "已核验", "确认"}:
                continue
            column = db.get(MetadataColumn, mapping.metadata_column_id)
            table = db.get(MetadataTable, column.table_id) if column else None
            if not column or not table:
                continue
            if version.required:
                candidates.append({"candidate_code": f"STD-{version.id}-{column.id}-COMP",
                    "name": f"{standard.name if standard else '标准'} - 完整性检查",
                    "rule_type": "completeness", "severity": "中", "threshold_rate": 100,
                    "config": {}, "table_id": table.id, "column_id": column.id,
                    "standard_version_id": version.id, "enabled": False})
            rng = (version.value_range or "").strip()
            # Deliberately accept only simple numeric ranges; never execute arbitrary expressions.
            import re
            match = re.fullmatch(r"\\s*(-?\\d+(?:\\.\\d+)?)\\s*(?:~|至|-)\\s*(-?\\d+(?:\\.\\d+)?)\\s*", rng)
            if match and column.data_type.lower().find("char") == -1 and column.data_type.lower().find("text") == -1:
                candidates.append({"candidate_code": f"STD-{version.id}-{column.id}-RANGE",
                    "name": f"{standard.name if standard else '标准'} - 范围检查",
                    "rule_type": "range", "severity": "中", "threshold_rate": 100,
                    "config": {"min": float(match.group(1)), "max": float(match.group(2))},
                    "table_id": table.id, "column_id": column.id,
                    "standard_version_id": version.id, "enabled": False})
    return {"count": len(candidates), "candidates": candidates,
        "notice": "只生成候选预览，不创建或启用规则；仅依据已发布标准和已确认映射。"}

@app.get("/api/v1/quality/rules")
def list_quality_rules(
    keyword: str | None = None,
    rule_type: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(db_session),
):
    stmt = select(QualityRule).order_by(QualityRule.updated_at.desc(), QualityRule.id.desc())
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(QualityRule.name.ilike(like) | QualityRule.rule_code.ilike(like))
    if rule_type:
        stmt = stmt.where(QualityRule.rule_type == rule_type)
    if enabled is not None:
        stmt = stmt.where(QualityRule.enabled == enabled)
    return [quality_rule_public(row) for row in db.scalars(stmt).all()]


@app.post("/api/v1/quality/rules", status_code=201)
def create_quality_rule(
    payload: QualityRuleIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    if db.scalar(select(QualityRule).where(QualityRule.rule_code == payload.rule_code)):
        raise HTTPException(409, "质量规则编码已存在")
    table = db.get(MetadataTable, payload.metadata_table_id)
    column = db.get(MetadataColumn, payload.metadata_column_id)
    if not table or not column or column.table_id != table.id:
        raise HTTPException(400, "所选字段不属于指定元数据表")
    if payload.standard_version_id is not None and not db.get(DataStandardVersion, payload.standard_version_id):
        raise HTTPException(404, "关联的数据标准版本不存在")
    config = payload.config
    if payload.rule_type == "range":
        if "min" not in config and "max" not in config:
            raise HTTPException(422, "范围规则至少需要配置 min 或 max")
        for key in ("min", "max"):
            if key in config and not isinstance(config[key], (int, float)):
                raise HTTPException(422, "范围边界必须为数字")
        if "min" in config and "max" in config and config["min"] > config["max"]:
            raise HTTPException(422, "范围规则 min 不能大于 max")
    if payload.rule_type == "enum":
        values = config.get("allowed_values")
        if not isinstance(values, list) or not values or len(values) > 500:
            raise HTTPException(422, "枚举规则必须配置 1-500 个 allowed_values")
        if any(not isinstance(value, (str, int, float, bool)) for value in values):
            raise HTTPException(422, "枚举值只能是字符串、数字或布尔值")
    if payload.rule_type in {"completeness", "uniqueness"} and config:
        raise HTTPException(422, "该规则类型不接受额外配置")
    row = QualityRule(
        **payload.model_dump(exclude={"config"}),
        config=json.dumps(config, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return quality_rule_public(row)


@app.patch("/api/v1/quality/rules/{rule_id}")
def update_quality_rule(
    rule_id: int,
    payload: dict,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(QualityRule, rule_id)
    if not row:
        raise HTTPException(404, "质量规则不存在")
    if "enabled" in payload:
        row.enabled = bool(payload["enabled"])
    if "severity" in payload:
        if payload["severity"] not in {"低", "中", "高"}:
            raise HTTPException(422, "无效的严重级别")
        row.severity = payload["severity"]
    if "threshold_rate" in payload:
        try:
            value = float(payload["threshold_rate"])
        except (TypeError, ValueError):
            raise HTTPException(422, "通过率阈值必须为数字")
        if not 0 <= value <= 100:
            raise HTTPException(422, "通过率阈值必须在 0-100 之间")
        row.threshold_rate = value
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return quality_rule_public(row)


def run_quality_rule(rule_id: int, db: Session):
    rule = db.get(QualityRule, rule_id)
    if not rule:
        raise HTTPException(404, "质量规则不存在")
    if not rule.enabled:
        raise HTTPException(409, "该质量规则已停用")
    metadata_table = db.get(MetadataTable, rule.metadata_table_id)
    metadata_column = db.get(MetadataColumn, rule.metadata_column_id)
    source = db.get(DataSource, metadata_table.source_id) if metadata_table else None
    if not metadata_table or not metadata_column or metadata_column.table_id != metadata_table.id or not source:
        raise HTTPException(409, "规则关联的元数据对象已失效，请重新配置规则")
    run = QualityRun(rule_id=rule.id, status="运行中", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)
    source_engine = None
    try:
        source_engine = build_source_engine(source)
        reflected = Table(
            metadata_table.table_name, MetaData(), schema=metadata_table.schema_name or None,
            autoload_with=source_engine,
        )
        column = reflected.c.get(metadata_column.column_name)
        if column is None:
            raise ValueError("源数据库中已找不到该字段，请重新采集元数据")
        config = json.loads(rule.config or "{}")
        if rule.rule_type == "completeness":
            invalid = column.is_(None)
        elif rule.rule_type == "uniqueness":
            duplicates = select(column.label("value"), func.count().label("duplicate_count")).where(
                column.is_not(None)
            ).group_by(column).having(func.count() > 1).subquery()
            failed_statement = select(func.coalesce(func.sum(duplicates.c.duplicate_count), 0))
            with source_engine.connect() as conn:
                total = conn.scalar(select(func.count()).select_from(reflected)) or 0
                failed = conn.scalar(failed_statement) or 0
            run.total_count = int(total)
            run.failed_count = int(failed)
            run.message = "重复值按涉及的重复记录数统计；NULL 不参与唯一性判断。"
            invalid = None
        elif rule.rule_type == "range":
            clauses = []
            if "min" in config:
                clauses.append(column < config["min"])
            if "max" in config:
                clauses.append(column > config["max"])
            invalid = and_(column.is_not(None), or_(*clauses))
        elif rule.rule_type == "enum":
            invalid = and_(column.is_not(None), column.not_in(config["allowed_values"]))
        else:
            raise ValueError("不支持的质量规则类型")
        if invalid is not None:
            with source_engine.connect() as conn:
                total = conn.scalar(select(func.count()).select_from(reflected)) or 0
                failed = conn.scalar(select(func.count()).select_from(reflected).where(invalid)) or 0
            run.total_count = int(total)
            run.failed_count = int(failed)
        pass_rate = 100.0 if run.total_count == 0 else max(0.0, (run.total_count - run.failed_count) / run.total_count * 100)
        run.pass_rate = round(pass_rate, 2)
        run.passed = pass_rate >= rule.threshold_rate
        run.status = "成功"
        run.message = run.message or "只读检测完成，未修改源数据库数据。"
        run.finished_at = datetime.utcnow()
        db.commit()
        return {
            "id": run.id, "rule_id": run.rule_id, "status": run.status,
            "total_count": run.total_count, "failed_count": run.failed_count,
            "pass_rate": run.pass_rate, "passed": run.passed, "message": run.message,
            "started_at": run.started_at, "finished_at": run.finished_at,
        }
    except Exception as exc:
        db.rollback()
        failed_run = db.get(QualityRun, run.id)
        failed_run.status = "失败"
        failed_run.message = f"检测失败：{type(exc).__name__}。请检查源库连接、字段类型和只读账号权限。"
        failed_run.finished_at = datetime.utcnow()
        db.commit()
        return {
            "id": failed_run.id, "rule_id": failed_run.rule_id, "status": failed_run.status,
            "total_count": failed_run.total_count, "failed_count": failed_run.failed_count,
            "pass_rate": failed_run.pass_rate, "passed": False, "message": failed_run.message,
            "started_at": failed_run.started_at, "finished_at": failed_run.finished_at,
        }
    finally:
        if source_engine is not None:
            source_engine.dispose()


@app.post("/api/v1/quality/rules/{rule_id}/run")
def execute_quality_rule(
    rule_id: int,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    return run_quality_rule(rule_id, db)


@app.get("/api/v1/quality/rules/{rule_id}/runs")
def list_quality_runs(rule_id: int, db: Session = Depends(db_session)):
    if not db.get(QualityRule, rule_id):
        raise HTTPException(404, "质量规则不存在")
    rows = db.scalars(select(QualityRun).where(QualityRun.rule_id == rule_id).order_by(QualityRun.id.desc()).limit(20)).all()
    return [{
        "id": row.id, "rule_id": row.rule_id, "status": row.status,
        "total_count": row.total_count, "failed_count": row.failed_count,
        "pass_rate": row.pass_rate, "passed": row.passed, "message": row.message,
        "started_at": row.started_at, "finished_at": row.finished_at,
    } for row in rows]



def issue_public(row: GovernanceIssue):
    return {
        "id": row.id, "issue_code": row.issue_code, "quality_run_id": row.quality_run_id,
        "rule_id": row.rule_id, "title": row.title, "description": row.description,
        "severity": row.severity, "owner_department": row.owner_department, "owner": row.owner,
        "status": row.status, "due_date": row.due_date, "remediation_note": row.remediation_note,
        "review_note": row.review_note, "last_recheck_run_id": row.last_recheck_run_id,
        "created_at": row.created_at, "updated_at": row.updated_at, "closed_at": row.closed_at,
    }


@app.get("/api/v1/issues")
def list_governance_issues(
    keyword: str | None = None,
    status: str | None = None,
    owner_department: str | None = None,
    db: Session = Depends(db_session),
):
    stmt = select(GovernanceIssue).order_by(GovernanceIssue.updated_at.desc(), GovernanceIssue.id.desc())
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(GovernanceIssue.issue_code.ilike(like) | GovernanceIssue.title.ilike(like) |
                          GovernanceIssue.description.ilike(like) | GovernanceIssue.owner.ilike(like))
    if status:
        stmt = stmt.where(GovernanceIssue.status == status)
    if owner_department:
        stmt = stmt.where(GovernanceIssue.owner_department == owner_department)
    return [issue_public(row) for row in db.scalars(stmt).all()]


@app.post("/api/v1/issues", status_code=201)
def create_governance_issue(
    payload: GovernanceIssueCreateIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    run = db.get(QualityRun, payload.quality_run_id)
    if not run or run.status != "成功":
        raise HTTPException(404, "有效的质量检测记录不存在")
    if run.failed_count <= 0:
        raise HTTPException(409, "检测结果没有异常记录，无需创建治理问题")
    rule = db.get(QualityRule, run.rule_id)
    if not rule:
        raise HTTPException(409, "质量规则已不存在")
    row = GovernanceIssue(
        issue_code="GOV-" + uuid4().hex[:10].upper(),
        quality_run_id=run.id, rule_id=rule.id,
        title=payload.title, description=payload.description,
        severity=payload.severity, owner_department=payload.owner_department,
        owner=payload.owner, due_date=payload.due_date,
        status="待分派",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return issue_public(row)


@app.get("/api/v1/issues/{issue_id}")
def get_governance_issue(issue_id: int, db: Session = Depends(db_session)):
    row = db.get(GovernanceIssue, issue_id)
    if not row:
        raise HTTPException(404, "治理问题不存在")
    result = issue_public(row)
    if row.quality_run_id:
        original = db.get(QualityRun, row.quality_run_id)
        result["original_run"] = {
            "total_count": original.total_count, "failed_count": original.failed_count,
            "pass_rate": original.pass_rate,
        } if original else None
    if row.last_recheck_run_id:
        recheck = db.get(QualityRun, row.last_recheck_run_id)
        result["last_recheck"] = {
            "total_count": recheck.total_count, "failed_count": recheck.failed_count,
            "pass_rate": recheck.pass_rate, "status": recheck.status,
        } if recheck else None
    return result


@app.patch("/api/v1/issues/{issue_id}/assign")
def assign_governance_issue(
    issue_id: int,
    payload: GovernanceIssueAssignIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(GovernanceIssue, issue_id)
    if not row:
        raise HTTPException(404, "治理问题不存在")
    if row.status in {"待关闭", "已关闭"}:
        raise HTTPException(409, "问题已进入关闭阶段，不能重新分派")
    row.owner_department = payload.owner_department
    row.owner = payload.owner
    row.due_date = payload.due_date
    row.status = "整改中"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return issue_public(row)


@app.patch("/api/v1/issues/{issue_id}/remediation")
def submit_issue_remediation(
    issue_id: int,
    payload: GovernanceIssueRemediationIn,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(GovernanceIssue, issue_id)
    if not row:
        raise HTTPException(404, "治理问题不存在")
    if row.status != "整改中" or not row.owner:
        raise HTTPException(409, "请先分派责任人，再提交整改说明")
    row.remediation_note = payload.remediation_note
    row.status = "待复测"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return issue_public(row)


@app.post("/api/v1/issues/{issue_id}/recheck")
def recheck_governance_issue(
    issue_id: int,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(GovernanceIssue, issue_id)
    if not row:
        raise HTTPException(404, "治理问题不存在")
    if row.status != "待复测" or not row.rule_id:
        raise HTTPException(409, "问题必须处于待复测状态")
    result = run_quality_rule(row.rule_id, db)
    row = db.get(GovernanceIssue, issue_id)
    row.last_recheck_run_id = result.get("id")
    if result.get("status") == "成功" and result.get("failed_count") == 0:
        row.status = "待关闭"
        row.review_note = "复测通过：异常记录数为 0，等待治理负责人确认关闭。"
    elif result.get("status") == "成功":
        row.status = "整改中"
        row.review_note = "复测未通过：仍存在 " + str(result.get("failed_count", 0)) + " 条异常记录。"
    else:
        row.status = "整改中"
        row.review_note = "复测执行失败：" + str(result.get("message", "请检查数据源连接和权限。") )
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return {**issue_public(row), "recheck_result": result}


@app.post("/api/v1/issues/{issue_id}/close")
def close_governance_issue(
    issue_id: int,
    _user: User = Depends(require_permission("governance:write")),
    db: Session = Depends(db_session),
):
    row = db.get(GovernanceIssue, issue_id)
    if not row:
        raise HTTPException(404, "治理问题不存在")
    if row.status != "待关闭" or not row.last_recheck_run_id:
        raise HTTPException(409, "问题尚未复测通过，不能关闭")
    recheck = db.get(QualityRun, row.last_recheck_run_id)
    if not recheck or recheck.status != "成功" or recheck.failed_count != 0:
        raise HTTPException(409, "最近一次复测仍有异常，不能关闭")
    row.status = "已关闭"
    row.closed_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return issue_public(row)


@app.post("/api/v1/agents/run")
def agent_run(
    payload: AgentPrompt,
    _user: User = Depends(require_permission("governance:read")),
    db: Session = Depends(db_session),
):
    # Only aggregate counters are assembled here; no source connection details,
    # metadata identifiers, business rows, or personal information enter model context.
    context = {
        "assets": db.scalar(select(func.count()).select_from(DataAsset)) or 0,
        "standards": db.scalar(select(func.count()).select_from(DataStandard)) or 0,
        "quality_rules": db.scalar(select(func.count()).select_from(QualityRule)) or 0,
        "open_issues": db.scalar(select(func.count()).select_from(GovernanceIssue).where(
            GovernanceIssue.status != "已关闭"
        )) or 0,
        "unclassified_columns": db.scalar(select(func.count()).select_from(MetadataColumn).where(
            MetadataColumn.sensitivity_level == "未分级"
        )) or 0,
        "sensitive_columns": db.scalar(select(func.count()).select_from(MetadataColumn).where(
            MetadataColumn.sensitivity_level.in_(["敏感", "高度敏感"])
        )) or 0,
    }
    result = run_governance_agent(
        payload.prompt, context, allow_external_model=payload.allow_external_model
    )
    return {
        "status": "success",
        "agent": "governance-assistant",
        "context_scope": "aggregate_only",
        **result,
    }

@app.get("/api/v1/finereport/reports/{report_id}/lineage-preview")
def finereport_lineage_preview(report_id: str, db: Session = Depends(db_session)):
    """Read-only, unconfirmed report SQL lineage preview; SQL is never executed."""
    report_row = db.scalar(select(Record).where(
        Record.category == "finereport_report", Record.name == report_id
    ))
    if not report_row:
        raise HTTPException(404, "FineReport报表不存在")
    try:
        inventory = json.loads(report_row.description or "{}")
    except (TypeError, json.JSONDecodeError):
        inventory = {}

    datasets = []
    raw_datasets = inventory.get("datasets")
    if isinstance(raw_datasets, list):
        for i, item in enumerate(raw_datasets):
            if isinstance(item, dict) and isinstance(item.get("sql"), str):
                datasets.append({"dataset": str(item.get("name") or item.get("id") or f"dataset_{i+1}"), "sql": item["sql"]})
            elif isinstance(item, str):
                datasets.append({"dataset": f"dataset_{i+1}", "sql": item})
    elif isinstance(raw_datasets, dict):
        for name, item in raw_datasets.items():
            if isinstance(item, dict) and isinstance(item.get("sql"), str):
                datasets.append({"dataset": str(name), "sql": item["sql"]})
            elif isinstance(item, str):
                datasets.append({"dataset": str(name), "sql": item})
    if isinstance(inventory.get("dataset_sql"), str) and inventory["dataset_sql"].strip():
        datasets.append({"dataset": "dataset_sql", "sql": inventory["dataset_sql"]})

    catalog = db.scalars(select(MetadataTable)).all()
    previews = []
    for dataset in datasets:
        extracted = extract_sql_table_references(dataset["sql"])
        matched, unresolved, ambiguous = [], [], []
        for reference in extracted["tables"]:
            parts = reference.split(".")
            table_name = parts[-1].strip().casefold()
            schema_name = parts[-2].strip().casefold() if len(parts) >= 2 else None
            candidates = [t for t in catalog if t.table_name.casefold() == table_name
                          and (schema_name is None or (t.schema_name or "").casefold() == schema_name)]
            if len(candidates) == 1:
                matched.append({"reference": reference, "table_id": candidates[0].id,
                               "source_id": candidates[0].source_id,
                               "schema_name": candidates[0].schema_name,
                               "table_name": candidates[0].table_name})
            elif len(candidates) > 1:
                ambiguous.append({"reference": reference, "candidate_table_ids": [t.id for t in candidates]})
            else:
                unresolved.append(reference)
        previews.append({"dataset": dataset["dataset"], "references": extracted["tables"],
                         "matched": matched, "unresolved": unresolved, "ambiguous": ambiguous,
                         "review_required": extracted["review_required"] or bool(unresolved) or bool(ambiguous),
                         "parser_reason": extracted["reason"]})
    return {"report_id": report_id, "report_name": inventory.get("name") or inventory.get("report_name") or report_row.name,
            "preview_only": True, "sql_executed": False, "datasets": previews,
            "review_required": not previews or any(item["review_required"] for item in previews)}



@app.get("/api/v1/governance/standard-coverage")
def s21_standard_coverage(_user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    """Read-only standard coverage and mapping review analytics."""
    tables = db.scalars(select(MetadataTable)).all()
    columns = db.scalars(select(MetadataColumn)).all()
    versions = db.scalars(select(DataStandardVersion)).all()
    standards = db.scalars(select(DataStandard)).all()
    published = {v.id for v in versions if v.status == "已发布"}
    mappings = db.scalars(select(DataStandardMapping)).all()
    confirmed = {m.metadata_column_id for m in mappings if m.version_id in published and m.mapping_status in ("已确认", "已通过", "已映射")}
    pending = sum(1 for m in mappings if m.mapping_status == "待核验")
    rejected = sum(1 for m in mappings if m.mapping_status in ("已拒绝", "拒绝"))
    domains = {}
    for standard in standards:
        domain = standard.business_domain or "未指定业务域"
        row = domains.setdefault(domain, {"standards": 0, "published_standards": 0, "mapped_columns": 0})
        row["standards"] += 1
        row["published_standards"] += sum(1 for v in standard.versions if v.status == "已发布")
    for mapping in mappings:
        if mapping.version_id in published and mapping.mapping_status in ("已确认", "已通过", "已映射"):
            ver = next((v for v in versions if v.id == mapping.version_id), None)
            std = next((s for s in standards if ver and s.id == ver.standard_id), None)
            if std:
                domains.setdefault(std.business_domain or "未指定业务域", {"standards": 0, "published_standards": 0, "mapped_columns": 0})["mapped_columns"] += 1
    unmapped = [{"column_id": c.id, "column": c.column_name, "table_id": c.table_id, "data_type": c.data_type, "sensitivity": c.sensitivity_level}
                for c in columns if c.id not in confirmed]
    return {"scope":{"tables":len(tables),"columns":len(columns),"standards":len(standards)},
        "published_standards":sum(1 for v in versions if v.status=="已发布"),
        "published_version_count":len(published),"confirmed_mapped_columns":len(confirmed),
        "mapping_coverage_pct":round(len(confirmed)/len(columns)*100,2) if columns else 0,
        "pending_reviews":pending,"rejected_reviews":rejected,"unmapped_columns":unmapped[:500],
        "unmapped_truncated":len(unmapped)>500,"business_domains":domains,
        "note":"Coverage is limited to collected metadata and published versions; mapping status is review-ledger data."}

@app.get("/api/v1/governance/quality-analytics")
def s22_quality_analytics(_user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    """Aggregate existing quality-run results; does not execute source queries."""
    rules = db.scalars(select(QualityRule)).all()
    runs = db.scalars(select(QualityRun).order_by(QualityRun.started_at.desc())).all()
    by_rule = {}
    for rule in rules:
        by_rule[rule.id] = {"rule_id":rule.id,"code":rule.rule_code,"name":rule.name,"enabled":rule.enabled,
            "runs":0,"latest_pass_rate":None,"latest_failed_count":None,"latest_status":None,"latest_at":None}
    for run in runs:
        item=by_rule.get(run.rule_id)
        if item:
            item["runs"]+=1
            if item["latest_at"] is None:
                item["latest_pass_rate"]=run.pass_rate;item["latest_failed_count"]=run.failed_count
                item["latest_status"]=run.status;item["latest_at"]=run.started_at
    completed=[r for r in runs if r.status in ("成功","完成","失败","异常")]
    return {"rules_total":len(rules),"enabled_rules":sum(1 for r in rules if r.enabled),
        "runs_total":len(runs),"completed_runs":len(completed),
        "successful_runs":sum(1 for r in completed if r.passed),
        "failed_runs":sum(1 for r in completed if not r.passed),
        "average_pass_rate":round(sum(r.pass_rate for r in completed)/len(completed),2) if completed else 0,
        "rules":sorted(by_rule.values(),key=lambda x:(x["latest_pass_rate"] is None,x["latest_pass_rate"] or 0)),
        "note":"Aggregates stored runs only; no new quality tests are executed."}

@app.get("/api/v1/governance/classification-analytics")
def s23_classification_analytics(_user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    """Read-only field classification coverage and risk-level inventory."""
    columns=db.scalars(select(MetadataColumn)).all()
    tables=db.scalars(select(MetadataTable)).all()
    levels=("公开","内部","敏感","高度敏感","未分级")
    distribution={level:sum(1 for c in columns if (c.sensitivity_level or "未分级")==level) for level in levels}
    unclassified=[{"column_id":c.id,"column":c.column_name,"table_id":c.table_id,"type":c.data_type}
        for c in columns if not c.sensitivity_level or c.sensitivity_level=="未分级"]
    table_summary=[]
    for t in tables:
        cols=[c for c in columns if c.table_id==t.id]
        table_summary.append({"table_id":t.id,"schema":t.schema_name,"table":t.table_name,
            "column_count":len(cols),"classified_count":sum(1 for c in cols if c.sensitivity_level and c.sensitivity_level!="未分级"),
            "coverage_pct":round(sum(1 for c in cols if c.sensitivity_level and c.sensitivity_level!="未分级")/len(cols)*100,2) if cols else 0})
    return {"column_total":len(columns),"classified_count":len(columns)-len(unclassified),
        "coverage_pct":round((len(columns)-len(unclassified))/len(columns)*100,2) if columns else 0,
        "distribution":distribution,"unclassified_columns":unclassified[:500],"unclassified_truncated":len(unclassified)>500,
        "tables":table_summary,"note":"Classification coverage is within collected metadata only; levels require human confirmation."}

@app.get("/api/v1/governance/priorities")
def s24_governance_priorities(_user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    """Transparent, advisory issue/rule priority queue; no automatic assignment or remediation."""
    now=datetime.utcnow()
    issues=db.scalars(select(GovernanceIssue)).all()
    severity_weight={"高":40,"严重":50,"中":25,"低":10}
    status_weight={"待分派":10,"整改中":5,"待复测":8,"待关闭":2}
    priority_rows=[]
    for issue in issues:
        if issue.status=="已关闭": continue
        overdue=bool(issue.due_date and issue.due_date<now)
        score=severity_weight.get(issue.severity,15)+status_weight.get(issue.status,0)+(25 if overdue else 0)
        priority_rows.append({"type":"issue","id":issue.id,"code":issue.issue_code,"title":issue.title,
            "severity":issue.severity,"status":issue.status,"owner_department":issue.owner_department,
            "due_date":issue.due_date,"overdue":overdue,"score":score,
            "reason":"逾期" if overdue else "按严重级别和当前流程状态计算"})
    rules=db.scalars(select(QualityRule).where(QualityRule.enabled==True)).all()
    latest_runs=db.scalars(select(QualityRun).order_by(QualityRun.started_at.desc())).all()
    seen=set()
    for run in latest_runs:
        if run.rule_id in seen: continue
        seen.add(run.rule_id)
        rule=next((r for r in rules if r.id==run.rule_id),None)
        if rule and run.failed_count>0:
            score=severity_weight.get(rule.severity,15)+min(25,run.failed_count)
            priority_rows.append({"type":"quality_rule","id":rule.id,"code":rule.rule_code,"title":rule.name,
                "severity":rule.severity,"failed_count":run.failed_count,"pass_rate":run.pass_rate,
                "score":score,"reason":"最近一次已保存检测结果存在异常"})
    priority_rows.sort(key=lambda x:(x["score"],x.get("overdue",False)),reverse=True)
    return {"items":priority_rows[:100],"total":len(priority_rows),
        "scoring":"建议排序分：严重级别基础分 + 流程状态加分 + 逾期加分；质量规则按严重级别和最近失败数加分。",
        "disclaimer":"该排序为辅助建议，不替代责任部门判断；不会自动分派、执行检测或修改数据。"}

@app.get("/api/v1/governance/maturity")
def s20_governance_maturity(_user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    """Read-only, transparent governance maturity indicators; each metric is a ratio, not a certification."""
    tables = db.scalars(select(MetadataTable)).all()
    columns = db.scalars(select(MetadataColumn)).all()
    assets = db.scalars(select(DataAsset)).all()
    standards = db.scalars(select(DataStandard)).all()
    versions = db.scalars(select(DataStandardVersion)).all()
    published_version_ids = {v.id for v in versions if v.status == "已发布"}
    mappings = db.scalars(select(DataStandardMapping)).all()
    mapped_column_ids = {m.metadata_column_id for m in mappings if m.version_id in published_version_ids and m.mapping_status in ("已确认", "已通过", "已映射")}
    rules = db.scalars(select(QualityRule).where(QualityRule.enabled == True)).all()
    classified_columns = [col for col in columns if col.sensitivity_level and col.sensitivity_level != "未分级"]
    rule_column_ids = {r.metadata_column_id for r in rules}
    registered_table_ids = {a.metadata_table_id for a in assets if a.metadata_table_id is not None}
    issue_rows = db.scalars(select(GovernanceIssue)).all()
    closed_count = sum(1 for issue in issue_rows if issue.status == "已关闭")
    def ratio(n, d):
        return round(n / d * 100, 2) if d else 0.0
    metrics = [
        {"key":"asset_registration","label":"数据资产登记率","numerator":len(registered_table_ids),"denominator":len(tables),"value":ratio(len(registered_table_ids),len(tables)),"definition":"已登记为数据资产的元数据表 / 已采集元数据表"},
        {"key":"metadata_coverage","label":"元数据采集覆盖","numerator":len(tables),"denominator":len(tables),"value":100.0 if tables else 0.0,"definition":"工作台已采集的表数量；不是企业全库覆盖率"},
        {"key":"standard_mapping","label":"已确认标准映射率","numerator":len(mapped_column_ids),"denominator":len(columns),"value":ratio(len(mapped_column_ids),len(columns)),"definition":"映射到已发布标准且映射状态已确认的字段 / 已采集字段"},
        {"key":"classification","label":"字段分类分级率","numerator":len(classified_columns),"denominator":len(columns),"value":ratio(len(classified_columns),len(columns)),"definition":"已设置敏感级别且不为未分级的字段 / 已采集字段"},
        {"key":"quality_rule_coverage","label":"质量规则覆盖率","numerator":len(rule_column_ids),"denominator":len(columns),"value":ratio(len(rule_column_ids),len(columns)),"definition":"配置启用质量规则的字段数 / 已采集字段数"},
        {"key":"issue_closure","label":"治理问题关闭率","numerator":closed_count,"denominator":len(issue_rows),"value":ratio(closed_count,len(issue_rows)),"definition":"已关闭治理问题 / 治理问题总数"},
    ]
    score = round(sum(item["value"] for item in metrics) / len(metrics), 2)
    return {"score":score,"level":"初步建设" if score < 30 else "基础建设" if score < 60 else "规范建设" if score < 80 else "持续优化","metrics":metrics,
            "summary":{"metadata_tables":len(tables),"metadata_columns":len(columns),"registered_assets":len(registered_table_ids),"standards":len(standards),"enabled_quality_rules":len(rules),"issues":len(issue_rows),"closed_issues":closed_count},
            "disclaimer":"该评分为工作台内可见治理对象的参考指标，不代表企业整体治理成熟度或审计认证。请补充数据源范围、业务系统覆盖和人工核验后使用。"}

@app.get("/api/v1/governance/overview")
def s16_governance_overview(_user: User=Depends(require_permission("governance:read")),db:Session=Depends(db_session)):
    issues=db.scalars(select(GovernanceIssue)).all()
    now=datetime.utcnow()
    active=[i for i in issues if i.status!="已关闭"]
    closed=[i for i in issues if i.status=="已关闭"]
    overdue=[i for i in active if i.due_date and i.due_date<now]
    runs=db.scalars(select(QualityRun).order_by(QualityRun.id.desc())).all()
    latest_issues=sorted(issues,key=lambda i:i.updated_at or i.created_at or now,reverse=True)[:10]
    def grouped(items,key):
        result={}
        for item in items: result[str(key(item) or "未指定")]=result.get(str(key(item) or "未指定"),0)+1
        return result
    return {"issue_total":len(issues),"active_count":len(active),"closed_count":len(closed),
        "overdue_count":len(overdue),"closure_rate":round(len(closed)/len(issues)*100,2) if issues else 0,
        "status_distribution":grouped(issues,lambda i:i.status),
        "severity_distribution":grouped(issues,lambda i:i.severity),
        "department_distribution":grouped(active,lambda i:i.owner_department),
        "quality_runs":{"total":len(runs),"success":sum(1 for r in runs if r.status in ("成功","完成") and r.passed),
            "failed":sum(1 for r in runs if r.status in ("失败","异常") or not r.passed)},
        "latest_issues":[{"id":i.id,"issue_code":i.issue_code,"title":i.title,"severity":i.severity,
            "owner_department":i.owner_department,"owner":i.owner,"status":i.status,"due_date":i.due_date,
            "updated_at":i.updated_at} for i in latest_issues]}
