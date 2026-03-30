from http import HTTPStatus

from fastapi import Cookie, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token
from app.models import User


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not access_token:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    user_id = decode_access_token(access_token)
    if not user_id:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    return user
