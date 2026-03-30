from http import HTTPStatus

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import create_access_token, verify_password
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, csrf_protect: CsrfProtect = Depends(), error: str | None = None):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(request, "login.html", {"error": error, "csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    next_url: str = Query(default="/annotations/", alias="next"),
    session: AsyncSession = Depends(get_session),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)

    result = await session.exec(select(User).where(User.email == email))
    user = result.first()

    if not user or not verify_password(password, user.hashed_password):
        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
        response = templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid email or password", "csrf_token": csrf_token},
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        csrf_protect.set_csrf_cookie(signed_token, response)
        return response

    token = create_access_token(user.id)
    response = RedirectResponse(url=next_url, status_code=HTTPStatus.FOUND)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=HTTPStatus.FOUND)
    response.delete_cookie("access_token")
    return response
