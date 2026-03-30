import asyncio
import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect import CsrfProtect

from app.core.config import settings
from app.routers import annotations, auth, users
from app.services.browser import browser_manager


@CsrfProtect.load_config
def get_csrf_config():
    return [
        ("secret_key", settings.secret_key),
        ("token_location", "body"),
        ("token_key", "csrf_token"),
        ("cookie_samesite", "strict"),
        ("httponly", False),
    ]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await asyncio.to_thread(run_migrations)
    await browser_manager.start()
    yield
    await browser_manager.stop()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")


app.include_router(auth.router)
app.include_router(annotations.router)
app.include_router(users.router)
