from http import HTTPStatus

import pytest
from fastapi_csrf_protect import CsrfProtect
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session
from app.core.deps import get_current_user
from main import app

MOCK_PLAN = "1. Open trip.com\n2. Search for hotels in Warsaw\n3. Filter by 4 stars\n4. Sort by price"


class MockCsrfProtect:
    def generate_csrf_tokens(self):
        return "test_token", "test_signed_token"

    async def validate_csrf(self, request):
        pass

    def set_csrf_cookie(self, token, response):
        pass


@pytest.fixture
def client(session, user):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[CsrfProtect] = MockCsrfProtect
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test.net")
    app.dependency_overrides.clear()


async def test_generate_plan(client: AsyncClient, mocker):
    mocker.patch("app.routers.annotations.generate_plan", return_value=MOCK_PLAN)

    response = await client.post(
        "/annotations/generate-plan",
        data={"url": "https://trip.com", "prompt": "Find cheapest hotels in Warsaw"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["plan"] == MOCK_PLAN


async def test_annotation_detail(client: AsyncClient, annotation):
    response = await client.get(f"/annotations/{annotation.id}")
    assert response.status_code == HTTPStatus.OK
    assert annotation.url in response.text
    assert annotation.prompt in response.text


async def test_create_annotation_with_plan(client: AsyncClient, mocker):
    response = await client.post(
        "/annotations/",
        data={
            "url": "https://trip.com",
            "prompt": "Find cheapest hotels in Warsaw",
            "plan": MOCK_PLAN,
        },
    )
    assert response.status_code in (HTTPStatus.OK, HTTPStatus.FOUND)


async def test_annotations_list(client: AsyncClient, annotation):
    response = await client.get("/annotations/")
    assert response.status_code == HTTPStatus.OK
    assert annotation.url in response.text


async def test_annotation_new_page(client: AsyncClient):
    response = await client.get("/annotations/new")
    assert response.status_code == HTTPStatus.OK


async def test_annotation_not_found_redirects(client: AsyncClient):
    response = await client.get("/annotations/99999")
    assert response.status_code in (HTTPStatus.OK, HTTPStatus.FOUND)


async def test_generate_plan_error(client: AsyncClient, mocker):
    from app.ai.plan import PlanGenerationError

    mocker.patch("app.routers.annotations.generate_plan", side_effect=PlanGenerationError("API down"))

    response = await client.post(
        "/annotations/generate-plan",
        data={"url": "https://trip.com", "prompt": "Find hotels"},
    )

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert "API down" in response.json()["error"]


async def test_screenshot_success(client: AsyncClient, mocker):
    mocker.patch("app.services.browser.BrowserManager.take_screenshot", return_value="screenshots/test.png")
    mocker.patch("app.routers.annotations.validate_url", return_value=None)

    response = await client.post(
        "/annotations/screenshot",
        data={"url": "https://trip.com"},
    )

    assert response.status_code == HTTPStatus.OK
    assert "screenshot_url" in response.json()


async def test_screenshot_invalid_url(client: AsyncClient, mocker):
    mocker.patch("app.routers.annotations.validate_url", return_value="Invalid URL")

    response = await client.post(
        "/annotations/screenshot",
        data={"url": "not-a-url"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
