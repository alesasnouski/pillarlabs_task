import logging
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.security import hash_password
from app.models import User
from app.schemas.user import UserCreate, UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserPublic, status_code=HTTPStatus.CREATED)
async def create_user(body: UserCreate, session: AsyncSession = Depends(get_session)):
    try:
        user = User(
            username=body.username,
            email=body.email,
            hashed_password=hash_password(body.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError as e:
        error = str(e.orig)
        if "idx_users_email" in error:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail="Email already exists")
        if "idx_users_username" in error:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail="Username already exists")
        logger.exception("Unexpected integrity error for user: %s", body.email)
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail="User already exists")


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="User not found")
    return user
