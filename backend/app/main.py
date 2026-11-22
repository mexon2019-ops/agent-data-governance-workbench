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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint,
    create_engine, select, func, delete
)
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy import inspect as sa_inspect

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
    table: Mapped[MetadataTable] = relationship(back_populates="columns")


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


class AgentPrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)


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
def dashboard(_user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    counts = {c: db.scalar(select(func.count()).select_from(Record).where(Record.category == c)) or 0
              for c in ["asset", "standard", "quality", "task"]}
    counts["data_sources"] = db.scalar(select(func.count()).select_from(DataSource)) or 0
    counts["metadata_tables"] = db.scalar(select(func.count()).select_from(MetadataTable)) or 0
    counts["metadata_columns"] = db.scalar(select(func.count()).select_from(MetadataColumn)) or 0
    counts["pending_tasks"] = db.scalar(select(func.count()).select_from(Record).where(
        Record.category == "task", Record.status.in_(["待处理", "进行中", "草稿"]))) or 0
    return counts


@app.get("/api/v1/records")
def list_records(category: str | None = None, _user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    stmt = select(Record).order_by(Record.id.desc())
    if category:
        stmt = stmt.where(Record.category == category)
    return db.scalars(stmt).all()


@app.post("/api/v1/records", status_code=201)
def create_record(payload: RecordIn, _user: User = Depends(require_permission("governance:write")), db: Session = Depends(db_session)):
    row = Record(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.patch("/api/v1/records/{record_id}")
def update_record(record_id: int, payload: dict, _user: User = Depends(require_permission("governance:write")), db: Session = Depends(db_session)):
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
def delete_record(record_id: int, _user: User = Depends(require_permission("governance:write")), db: Session = Depends(db_session)):
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
def list_datasources(_user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
    return [datasource_public(x) for x in db.scalars(select(DataSource).order_by(DataSource.id.desc())).all()]


@app.post("/api/v1/datasources", status_code=201)
def create_datasource(payload: DataSourceIn, _user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
    if db.scalar(select(DataSource).where(DataSource.name == payload.name)):
        raise HTTPException(409, "数据源名称已存在")
    row = DataSource(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return datasource_public(row)


@app.patch("/api/v1/datasources/{source_id}")
def update_datasource(source_id: int, payload: DataSourceIn, _user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
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
def delete_datasource(source_id: int, _user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
    row = db.get(DataSource, source_id)
    if not row:
        raise HTTPException(404, "数据源不存在")
    db.delete(row)
    db.commit()


@app.post("/api/v1/datasources/{source_id}/test")
def test_datasource(source_id: int, _user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
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
                         _user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
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
def get_metadata_table(table_id: int, _user: User = Depends(require_permission("governance:read")), db: Session = Depends(db_session)):
    row = db.get(MetadataTable, table_id)
    if not row:
        raise HTTPException(404, "元数据表不存在")
    source = db.get(DataSource, row.source_id)
    return {
        **table_public(row, source.name if source else ""),
        "columns": [{
            "id": c.id, "column_name": c.column_name, "data_type": c.data_type,
            "nullable": c.nullable, "default_value": c.default_value,
            "ordinal_position": c.ordinal_position, "description": c.description,
            "is_primary_key": c.is_primary_key, "is_foreign_key": c.is_foreign_key
        } for c in row.columns]
    }


@app.get("/api/v1/datasources/{source_id}/sync-runs")
def list_sync_runs(source_id: int, _user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
    if not db.get(DataSource, source_id):
        raise HTTPException(404, "数据源不存在")
    rows = db.scalars(select(MetadataSyncRun).where(
        MetadataSyncRun.source_id == source_id).order_by(MetadataSyncRun.id.desc()).limit(20)).all()
    return rows


@app.post("/api/v1/datasources/{source_id}/sync")
def sync_metadata(source_id: int, _user: User = Depends(require_permission("datasource:manage")), db: Session = Depends(db_session)):
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
                    fk_cols = {col for fk in inspector.get_foreign_keys(table_name, schema=schema)
                               for col in (fk.get("constrained_columns") or [])}
                except Exception:
                    fk_cols = set()
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
                existing.columns.clear()
                # Flush orphan deletes before inserting columns with the same unique keys.
                db.flush()
                for index, col in enumerate(columns, start=1):
                    default = col.get("default")
                    existing.columns.append(MetadataColumn(
                        column_name=str(col.get("name", "")),
                        data_type=str(col.get("type", ""))[:255],
                        nullable=bool(col.get("nullable", True)),
                        default_value="" if default is None else str(default)[:1000],
                        ordinal_position=int(col.get("ordinal") or index),
                        description=str(col.get("comment") or "")[:4000],
                        is_primary_key=str(col.get("name", "")) in pk_cols,
                        is_foreign_key=str(col.get("name", "")) in fk_cols
                    ))
                table_count += 1
                column_count += len(columns)
        stale = db.scalars(select(MetadataTable).where(MetadataTable.source_id == source_id)).all()
        for old in stale:
            if (old.schema_name, old.table_name) not in discovered:
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


@app.post("/api/v1/agents/run")
def agent_run(payload: AgentPrompt, _user: User = Depends(require_permission("governance:write"))):
    return {"status": "draft", "agent": "governance-assistant",
            "reply": "已收到治理需求。当前版本先生成待审核建议；LangGraph 与模型网关将在后续版本接入。",
            "input_length": len(payload.prompt), "requires_human_approval": True}
