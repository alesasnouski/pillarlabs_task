import asyncio
import io
import json
import logging
import zipfile
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai.plan import PlanGenerationError, generate_plan
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models import Action, Annotation, Screenshot, User
from app.services.browser import (
    VIEWPORT,
    BrowserManager,
    ScreenshotError,
    get_browser_manager,
)
from app.services.url_validator import validate_url

logger = logging.getLogger(__name__)

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


@router.get("/export-all")
async def annotations_export_all(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    annotations = (
        await session.exec(select(Annotation).where(Annotation.user_id == current_user.id).order_by(Annotation.id))
    ).all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for annotation in annotations:
            ann_id = annotation.id
            actions = (
                await session.exec(select(Action).where(Action.annotation_id == ann_id).order_by(Action.id))
            ).all()
            screenshots = (
                await session.exec(select(Screenshot).where(Screenshot.annotation_id == ann_id).order_by(Screenshot.id))
            ).all()

            data = _serialize_annotation(annotation, list(actions), list(screenshots))
            zf.writestr(
                f"annotation_{ann_id}/annotation.json",
                json.dumps(data, indent=2, ensure_ascii=False),
            )

            # Include screenshot images
            for s in screenshots:
                img_path = Path("media") / s.image_path
                if img_path.exists():
                    zf.write(img_path, f"annotation_{ann_id}/{s.image_path}")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="annotations_export.zip"'},
    )


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
    result = await session.exec(
        select(Screenshot).where(Screenshot.annotation_id == annotation_id).order_by(Screenshot.id.desc())
    )
    screenshots = result.all()
    return templates.TemplateResponse(
        request,
        "annotation_detail.html",
        {"annotation": annotation, "screenshots": screenshots},
    )


@router.post("/screenshot")
async def annotation_screenshot(
    request: Request,
    url: str = Form(),
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
    browser_manager: BrowserManager = Depends(get_browser_manager),
):
    await csrf_protect.validate_csrf(request)

    error = validate_url(url)
    if error:
        return JSONResponse({"error": error}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)

    try:
        image_path = await browser_manager.take_screenshot(url)
        return JSONResponse({"screenshot_url": f"/media/{image_path}"})
    except ScreenshotError as e:
        return JSONResponse({"error": str(e)}, status_code=HTTPStatus.BAD_GATEWAY)


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
        logger.error("Plan generation failed: %s", e)
        return JSONResponse({"error": str(e)}, status_code=HTTPStatus.BAD_GATEWAY)


@router.post("/")
async def annotation_create(
    request: Request,
    url: str = Form(),
    prompt: str = Form(),
    plan: str = Form(""),
    screenshot_path: str = Form(""),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    assert current_user.id is not None

    annotation = Annotation(user_id=current_user.id, url=url, prompt=prompt, plan=plan)
    session.add(annotation)
    await session.flush()
    assert annotation.id is not None
    annotation_id = annotation.id

    if screenshot_path:
        screenshot = Screenshot(
            annotation_id=annotation.id,
            image_path=screenshot_path,
        )
        session.add(screenshot)

    await session.commit()
    return RedirectResponse(url=f"/annotations/{annotation_id}/session", status_code=HTTPStatus.FOUND)


@router.get("/{annotation_id}/session", response_class=HTMLResponse)
async def annotation_session(
    annotation_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
    browser_manager: BrowserManager = Depends(get_browser_manager),
):
    annotation = await session.get(Annotation, annotation_id)
    if not annotation or annotation.user_id != current_user.id:
        return RedirectResponse(url="/annotations/", status_code=HTTPStatus.FOUND)

    page = await browser_manager.get_or_create_page(annotation_id, annotation.url)

    result = await session.exec(select(Action).where(Action.annotation_id == annotation_id).order_by(Action.id))
    actions = result.all()

    result = await session.exec(
        select(Screenshot).where(Screenshot.annotation_id == annotation_id).order_by(Screenshot.id.desc())
    )
    latest_screenshot = result.first()

    # First session load (no actions yet) — take a fresh screenshot from the live page
    if not actions:
        image_path = await browser_manager.take_page_screenshot(page)
        new_screenshot = Screenshot(annotation_id=annotation_id, image_path=image_path)
        session.add(new_screenshot)
        await session.commit()
        latest_screenshot = new_screenshot

    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        request,
        "session.html",
        {
            "annotation": annotation,
            "screenshot": latest_screenshot,
            "actions": actions,
            "csrf_token": csrf_token,
        },
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post("/{annotation_id}/action")
async def annotation_action(
    annotation_id: int,
    request: Request,
    action_type: str = Form(),
    description: str = Form(),
    click_axis_x: int | None = Form(default=None),
    click_axis_y: int | None = Form(default=None),
    input_text: str | None = Form(default=None),
    final_result: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends(),
    browser_manager: BrowserManager = Depends(get_browser_manager),
):
    await csrf_protect.validate_csrf(request)

    annotation = await session.get(Annotation, annotation_id)
    if not annotation or annotation.user_id != current_user.id:
        return JSONResponse({"error": "Not found"}, status_code=HTTPStatus.NOT_FOUND)

    try:
        page = await browser_manager.get_or_create_page(annotation_id, annotation.url)

        if action_type == "click":
            if click_axis_x is None or click_axis_y is None:
                return JSONResponse({"error": "Missing click coordinates"}, status_code=HTTPStatus.BAD_REQUEST)
            if not (0 <= click_axis_x <= VIEWPORT["width"]):
                return JSONResponse({"error": f"X coordinate {click_axis_x} is out of bounds (0 - {VIEWPORT['width']})"}, status_code=HTTPStatus.BAD_REQUEST)
            if not (0 <= click_axis_y <= VIEWPORT["height"]):
                return JSONResponse({"error": f"Y coordinate {click_axis_y} is out of bounds (0 - {VIEWPORT['height']})"}, status_code=HTTPStatus.BAD_REQUEST)
            await browser_manager.perform_click(page, click_axis_x, click_axis_y)
        elif action_type == "type":
            if not input_text:
                return JSONResponse({"error": "Missing input text"}, status_code=HTTPStatus.BAD_REQUEST)
            await browser_manager.perform_type(page, input_text)
        elif action_type in ("scroll_up", "scroll_down"):
            await browser_manager.perform_scroll(page, action_type)

        image_path = await browser_manager.take_page_screenshot(page)

        screenshot = Screenshot(annotation_id=annotation_id, image_path=image_path)
        session.add(screenshot)
        await session.flush()

        assert annotation.id is not None
        assert screenshot.id is not None

        action = Action(
            annotation_id=annotation_id,
            screenshot_id=screenshot.id,
            type=action_type,
            click_axis_x=click_axis_x,
            click_axis_y=click_axis_y,
            input_text=input_text,
            description=description,
            final_result=final_result,
        )
        session.add(action)

        if action_type == "stop":
            annotation.status = "completed"
            session.add(annotation)
            await browser_manager.close_page(annotation_id)

        await session.commit()
        return JSONResponse({"screenshot_url": f"/media/{image_path}"})

    except PlaywrightTimeoutError as e:
        return JSONResponse({"error": str(e)}, status_code=HTTPStatus.BAD_GATEWAY)


def _serialize_annotation(
    annotation: Annotation,
    actions: list[Action],
    screenshots: list[Screenshot],
) -> dict:
    """Build a JSON-serializable dict for one annotation."""
    return {
        "id": annotation.id,
        "url": annotation.url,
        "prompt": annotation.prompt,
        "plan": annotation.plan,
        "status": annotation.status,
        "created_at": annotation.created_at.isoformat(),
        "actions": [
            {
                "step": idx + 1,
                "type": a.type,
                "click_x": a.click_axis_x,
                "click_y": a.click_axis_y,
                "input_text": a.input_text,
                "description": a.description,
                "final_result": a.final_result or None,
                "screenshot": a.screenshot_id,
                "created_at": a.created_at.isoformat(),
            }
            for idx, a in enumerate(actions)
        ],
        "screenshots": [
            {
                "id": s.id,
                "image_path": s.image_path,
                "viewport": f"{s.viewport_width}x{s.viewport_height}",
                "created_at": s.created_at.isoformat(),
            }
            for s in screenshots
        ],
    }


@router.get("/{annotation_id}/export")
async def annotation_export(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    annotation = await session.get(Annotation, annotation_id)
    if not annotation or annotation.user_id != current_user.id:
        return JSONResponse({"error": "Not found"}, status_code=HTTPStatus.NOT_FOUND)

    actions = (
        await session.exec(select(Action).where(Action.annotation_id == annotation_id).order_by(Action.id))
    ).all()
    screenshots = (
        await session.exec(select(Screenshot).where(Screenshot.annotation_id == annotation_id).order_by(Screenshot.id))
    ).all()

    data = _serialize_annotation(annotation, list(actions), list(screenshots))
    content = json.dumps(data, indent=2, ensure_ascii=False)

    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="annotation_{annotation_id}.json"'},
    )


@router.get("/{annotation_id}/export-zip")
async def annotation_export_zip(
    annotation_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    annotation = await session.get(Annotation, annotation_id)
    if not annotation or annotation.user_id != current_user.id:
        return JSONResponse({"error": "Not found"}, status_code=HTTPStatus.NOT_FOUND)

    actions = (
        await session.exec(select(Action).where(Action.annotation_id == annotation_id).order_by(Action.id))
    ).all()
    screenshots = (
        await session.exec(select(Screenshot).where(Screenshot.annotation_id == annotation_id).order_by(Screenshot.id))
    ).all()

    data = _serialize_annotation(annotation, list(actions), list(screenshots))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("annotation.json", json.dumps(data, indent=2, ensure_ascii=False))
        for s in screenshots:
            img_path = Path("media") / s.image_path
            if img_path.exists():
                zf.write(img_path, s.image_path)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="annotation_{annotation_id}.zip"'},
    )
