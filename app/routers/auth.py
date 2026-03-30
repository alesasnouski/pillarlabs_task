from http import HTTPStatus

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import create_access_token, verify_password
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password"}, status_code=HTTPStatus.UNAUTHORIZED
        )

    token = create_access_token(user.id)
    response = RedirectResponse(url="/annotations", status_code=HTTPStatus.FOUND)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=HTTPStatus.FOUND)
    response.delete_cookie("access_token")
    return response
