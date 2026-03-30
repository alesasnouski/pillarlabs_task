import uuid
from http import HTTPStatus

import pytest_asyncio
from fastapi_csrf_protect import CsrfProtect
from httpx import ASGITransport, AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import hash_password
from app.models import User
from main import app


class MockCsrfProtect:
    def generate_csrf_tokens(self):
        return "test_token", "test_signed_token"

    async def validate_csrf(self, request):
        pass

    def set_csrf_cookie(self, token, response):
        pass


@pytest_asyncio.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[CsrfProtect] = MockCsrfProtect
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test.net")
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user_with_password(session: AsyncSession) -> User:
    suffix = uuid.uuid4().hex[:8]
    u = User(
        username=f"authuser_{suffix}",
        email=f"auth_{suffix}@example.com",
        hashed_password=hash_password("correct_password"),
    )
    session.add(u)
    await session.flush()
    await session.refresh(u)
    return u


async def test_login_page(client: AsyncClient):
    response = await client.get("/auth/login")
    assert response.status_code == HTTPStatus.OK
    assert "Login" in response.text


async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        data={"email": "nobody@example.com", "password": "wrong", "csrf_token": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "Invalid" in response.text


async def test_login_success(client: AsyncClient, user_with_password: User):
    response = await client.post(
        "/auth/login",
        data={"email": user_with_password.email, "password": "correct_password", "csrf_token": "test"},
    )
    assert response.status_code in (HTTPStatus.OK, HTTPStatus.FOUND)


async def test_logout(client: AsyncClient):
    response = await client.get("/auth/logout")
    assert response.status_code == HTTPStatus.FOUND
