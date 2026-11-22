import os
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import quote_plus

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select, func
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

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

app = FastAPI(title="Agent 数据治理工作台 API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "data-governance-api", "version": "0.2.0"}

@app.get("/api/v1/dashboard")
def dashboard(db: Session = Depends(db_session)):
    counts = {c: db.scalar(select(func.count()).select_from(Record).where(Record.category == c)) or 0
              for c in ["asset", "standard", "quality", "task"]}
    counts["data_sources"] = db.scalar(select(func.count()).select_from(DataSource)) or 0
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
    password = os.getenv(row.password_env_key)
    if not password:
        raise HTTPException(400, f"服务端未配置环境变量 {row.password_env_key}；密码不会存入数据库")
    drivers = {
        "sqlserver": ("mssql+pymssql", {"login_timeout": 5}),
        "oracle": ("oracle+oracledb", {"tcp_connect_timeout": 5}),
        "mysql": ("mysql+pymysql", {"connect_timeout": 5}),
        "postgresql": ("postgresql+psycopg", {"connect_timeout": 5}),
    }
    dialect, connect_args = drivers[row.db_type]
    url = URL.create(dialect, username=row.username, password=password, host=row.host, port=row.port, database=row.database)
    try:
        test_engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        with test_engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        test_engine.dispose()
        row.status = "连接成功"
        result = {"success": True, "message": "连接成功"}
    except Exception as exc:
        row.status = "连接失败"
        result = {"success": False, "message": f"连接失败：{type(exc).__name__}，请检查网络、驱动和凭据配置"}
    row.last_test_at = datetime.utcnow()
    db.commit()
    return result

class AgentPrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

@app.post("/api/v1/agents/run")
def agent_run(payload: AgentPrompt):
    return {"status": "draft", "agent": "governance-assistant",
            "reply": "已收到治理需求。当前版本先生成待审核建议；LangGraph 与模型网关将在后续版本接入。",
            "input_length": len(payload.prompt), "requires_human_approval": True}
