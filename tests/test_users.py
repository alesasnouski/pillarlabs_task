import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.models import User
from main import app


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


async def test_get_user(client: AsyncClient, user: User):
    response = await client.get(f"/users/{user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/users/99999")
    assert response.status_code == 404


async def test_create_user(client: AsyncClient):
    response = await client.post("/users/", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "secret",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["is_active"] is True
