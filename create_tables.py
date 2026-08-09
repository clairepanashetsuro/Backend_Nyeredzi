import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from ivhuRedu.models import Base

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/ivhuredu_db"

async def create_tables():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Tables created successfully")

asyncio.run(create_tables())
