import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Annotation, User

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
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"testuser_{suffix}",
        email=f"test_{suffix}@example.com",
        hashed_password="hashed_secret",
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def annotation(session: AsyncSession, user: User) -> Annotation:
    assert user.id is not None
    a = Annotation(
        user_id=user.id,
        url="https://trip.com",
        prompt="Find cheapest hotels in Warsaw",
        plan="1. Open trip.com\n2. Search hotels",
    )
    session.add(a)
    await session.flush()
    await session.refresh(a)
    return a
