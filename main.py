import os
import ssl
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy async URL (postgresql+asyncpg)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SSL context for Neon
ssl_context = ssl.create_default_context()

# Async engine
engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1),
    echo=True,
    connect_args={"ssl": ssl_context}
)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# DB Model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)

# Pydantic schema
class UserCreate(BaseModel):
    username: str
    age: int

# FastAPI app
app = FastAPI()

# Dependency
async def get_session():
    async with SessionLocal() as session:
        yield session

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hello World from FastAPI 🚀"}

# POST endpoint
@app.post("/users")
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_session)):
    new_user = User(username=user.username, age=user.age)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "age": new_user.age}

# Auto-create tables on startup (for dev/demo)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
