import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.models import User
from app.schemas.user import UserCreate, UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserPublic, status_code=201)
async def create_user(body: UserCreate, session: AsyncSession = Depends(get_session)):
    try:
        user = User(
            username=body.username,
            email=body.email,
            hashed_password=body.password,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except Exception:
        logger.exception("Failed to create user: %s", body.email)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
