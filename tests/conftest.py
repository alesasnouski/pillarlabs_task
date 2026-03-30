import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

import app.models  # noqa: F401 — registers all table metadata
from app.models import User

TEST_DATABASE_URL = "postgresql+asyncpg://annotation:annotation@localhost:5432/annotation_tool"


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as s:
            yield s
        await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def user(session: AsyncSession) -> User:
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_secret",
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user
