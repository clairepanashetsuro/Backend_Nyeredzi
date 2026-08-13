import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base


load_dotenv()


database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set")


engine = create_async_engine(
    database_url,
    echo=True,
)


async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


Base = declarative_base()


async def get_db():
    async with async_session() as session:
        yield session