import asyncio
from http import HTTPStatus

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai.plan import PlanGenerationError, generate_plan
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
        select(Annotation).where(Annotation.user_id == current_user.id).order_by(Annotation.id.desc())
    )
    annotations = result.all()
    return templates.TemplateResponse(request, "annotations.html", {"annotations": annotations})


@router.get("/new", response_class=HTMLResponse)
async def annotation_new(
    request: Request,
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(request, "annotation_new.html", {"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.get("/{annotation_id}", response_class=HTMLResponse)
async def annotation_detail(
    annotation_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    annotation = await session.get(Annotation, annotation_id)
    if not annotation or annotation.user_id != current_user.id:
        return RedirectResponse(url="/annotations/", status_code=HTTPStatus.FOUND)
    return templates.TemplateResponse(request, "annotation_detail.html", {"annotation": annotation})


@router.post("/generate-plan")
async def annotation_generate_plan(
    request: Request,
    url: str = Form(),
    prompt: str = Form(),
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    try:
        plan = await asyncio.to_thread(generate_plan, url, prompt)
        return JSONResponse({"plan": plan})
    except PlanGenerationError as e:
        return JSONResponse({"error": str(e)}, status_code=HTTPStatus.BAD_GATEWAY)


@router.post("/")
async def annotation_create(
    request: Request,
    url: str = Form(),
    prompt: str = Form(),
    plan: str = Form(""),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    annotation = Annotation(user_id=current_user.id, url=url, prompt=prompt, plan=plan)
    session.add(annotation)
    await session.commit()
    return RedirectResponse(url="/annotations/", status_code=HTTPStatus.FOUND)
