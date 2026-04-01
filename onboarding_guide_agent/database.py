import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean

# We place the SQLite DB inside vectordb so it can easily map to the same persistent volume as ChromaDB.
os.makedirs("./vectordb", exist_ok=True)
DATABASE_URL = "sqlite+aiosqlite:///./vectordb/agent_state.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(String, primary_key=True, index=True) # Unique Escalation ID
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    step = Column(Integer)
    reason = Column(String)
    status = Column(String, default="pending") # pending, accepted, in_progress, resolved, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FailureLog(Base):
    __tablename__ = "failure_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True)
    session_id = Column(String, index=True)
    step = Column(Integer)
    attempt_count = Column(Integer, default=1)
    last_attempt_at = Column(DateTime, default=datetime.utcnow)
    
class InteractionLog(Base):
    """Relational reference table for interactions (actual text/embeddings map to ChromaDB)"""
    __tablename__ = "interaction_logs"
    id = Column(String, primary_key=True, index=True) # matches Chroma_id
    user_id = Column(String)
    session_id = Column(String)
    step_id = Column(String)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
