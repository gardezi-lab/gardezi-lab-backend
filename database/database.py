import os
import ssl
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Load env variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Neon needs async driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# SSL context (Neon always requires SSL)
ssl_context = ssl.create_default_context()

# Async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"ssl": ssl_context}
)

# Session
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class
Base = declarative_base()

# Dependency
# Dependency
async def get_db():   # <- naam same rakho
    async with SessionLocal() as session:
        yield session

