import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Agent 数据治理工作台 API", version="0.3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "data-governance-api", "version": "0.3.0"}


@app.get("/api/v1/dashboard")
def dashboard(db: Session = Depends(db_session)):
    counts = {c: db.scalar(select(func.count()).select_from(Record).where(Record.category == c)) or 0
              for c in ["asset", "standard", "quality", "task"]}
    counts["data_sources"] = db.scalar(select(func.count()).select_from(DataSource)) or 0
    counts["metadata_tables"] = db.scalar(select(func.count()).select_from(MetadataTable)) or 0
    counts["metadata_columns"] = db.scalar(select(func.count()).select_from(MetadataColumn)) or 0
    counts["pending_tasks"] = db.scalar(select(func.count()).select_from(Record).where(
        Record.category == "task", Record.status.in_(["待处理", "进行中", "草稿"]))) or 0
    return counts


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
        schemas = inspector.get_schema_names()
        excluded = {"information_schema", "performance_schema", "mysql", "sys",
                    "pg_catalog", "pg_toast", "information_schema", "sysaux", "system", "xdb"}
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
            except Exception:
                continue
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
        db.commit()
        return {"success": False, "run_id": run.id, "message": run.message}
    except Exception as exc:
        db.rollback()
        run = db.get(MetadataSyncRun, run.id)
        run.status = "失败"
        run.message = f"采集失败：{type(exc).__name__}。请检查网络、账号权限和数据库驱动。"
        run.finished_at = datetime.utcnow()
        db.commit()
        return {"success": False, "run_id": run.id, "message": run.message}
    finally:
        if source_engine is not None:
            source_engine.dispose()


@app.post("/api/v1/agents/run")
def agent_run(payload: AgentPrompt):
    return {"status": "draft", "agent": "governance-assistant",
            "reply": "已收到治理需求。当前版本先生成待审核建议；LangGraph 与模型网关将在后续版本接入。",
            "input_length": len(payload.prompt), "requires_human_approval": True}
