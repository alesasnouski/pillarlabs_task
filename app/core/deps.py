from http import HTTPStatus

from fastapi import Cookie, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models import User


def _redirect_to_login(path: str) -> HTTPException:
    return HTTPException(
        status_code=HTTPStatus.FOUND,
        headers={"Location": f"/auth/login?next={path}"},
    )


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not access_token:
        raise _redirect_to_login(request.url.path)
    user_id = decode_access_token(access_token)
    if not user_id:
        raise _redirect_to_login(request.url.path)
    user = await session.get(User, user_id)
    if not user:
        raise _redirect_to_login(request.url.path)
    return user
