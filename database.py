import os
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

LOCAL_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ivhuredu_db"
)

database_url = os.getenv("DATABASE_URL", LOCAL_DATABASE_URL)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql+asyncpg://", 1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )

engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async_session = SessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async database session for incoming FastAPI requests
    and guarantees its safe closure afterward.
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

Base = declarative_base()
