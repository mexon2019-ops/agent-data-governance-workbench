import os
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./dev.db")
engine=create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass
class Record(Base):
    __tablename__="governance_records"
    id: Mapped[int]=mapped_column(primary_key=True)
    category: Mapped[str]=mapped_column(String(40),index=True)
    name: Mapped[str]=mapped_column(String(180))
    description: Mapped[str]=mapped_column(Text,default="")
    status: Mapped[str]=mapped_column(String(40),default="草稿")
    owner: Mapped[str]=mapped_column(String(100),default="")
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class RecordIn(BaseModel):
    category: str=Field(min_length=1,max_length=40)
    name: str=Field(min_length=1,max_length=180)
    description: str=""
    status: str="草稿"
    owner: str=""

def db_session():
    db=SessionLocal()
    try: yield db
    finally: db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield

app=FastAPI(title="Agent 数据治理工作台 API",version="0.1.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

@app.get("/health")
def health(): return {"status":"ok","service":"data-governance-api"}

@app.get("/api/v1/records")
def list_records(category: str|None=None, db: Session=Depends(db_session)):
    stmt=select(Record).order_by(Record.id.desc())
    if category: stmt=stmt.where(Record.category==category)
    return db.scalars(stmt).all()

@app.post("/api/v1/records",status_code=201)
def create_record(payload: RecordIn, db: Session=Depends(db_session)):
    row=Record(**payload.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

@app.patch("/api/v1/records/{record_id}")
def update_record(record_id:int,payload:dict,db:Session=Depends(db_session)):
    row=db.get(Record,record_id)
    if not row: raise HTTPException(404,"记录不存在")
    for k,v in payload.items():
        if k in {"category","name","description","status","owner"}: setattr(row,k,v)
    db.commit(); db.refresh(row); return row

@app.delete("/api/v1/records/{record_id}",status_code=204)
def delete_record(record_id:int,db:Session=Depends(db_session)):
    row=db.get(Record,record_id)
    if not row: raise HTTPException(404,"记录不存在")
    db.delete(row); db.commit()

class AgentPrompt(BaseModel):
    prompt: str=Field(min_length=1,max_length=4000)

@app.post("/api/v1/agents/run")
def agent_run(payload:AgentPrompt):
    return {"status":"draft","agent":"governance-assistant","reply":"Agent 接口骨架已就绪。下一阶段接入 LangGraph、模型网关、脱敏策略和人工审批。","input_length":len(payload.prompt),"requires_human_approval":True}
