
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models import Annotation, User

router = APIRouter(prefix="/annotations", tags=["annotations"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def annotations_list(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.exec(
        select(Annotation)
        .where(Annotation.user_id == current_user.id)
        .order_by(Annotation.created_at.desc())
    )
    annotations = result.all()
    return templates.TemplateResponse(request, "annotations.html", {"annotations": annotations})
