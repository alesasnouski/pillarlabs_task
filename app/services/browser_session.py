import asyncio
import logging
import uuid
from pathlib import Path

from playwright.async_api import Browser, Page, ViewportSize
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("media/screenshots")
VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}

_browser: Browser | None = None
_pages: dict[int, Page] = {}


def get_browser() -> Browser:
    """Return the shared browser instance (must be started first)."""
    assert _browser is not None, "Browser not started"
    return _browser


async def start_browser() -> None:
    global _browser
    playwright = await async_playwright().start()
    _browser = await playwright.chromium.launch(headless=True)
    logger.info("Browser started")


async def stop_browser() -> None:
    global _browser
    if _browser:
        await _browser.close()
        _browser = None
        logger.info("Browser stopped")


async def get_or_create_page(annotation_id: int, url: str) -> Page:
    if annotation_id not in _pages:
        assert _browser is not None, "Browser not started"
        page = await _browser.new_page(viewport=VIEWPORT)
        await page.goto(url, wait_until="load", timeout=30_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=5_000)
        except PlaywrightTimeoutError:
            pass
        await _wait_for_render(page)
        _pages[annotation_id] = page
        logger.info("Created page for annotation %d", annotation_id)
    return _pages[annotation_id]


async def close_page(annotation_id: int) -> None:
    if annotation_id in _pages:
        await _pages[annotation_id].close()
        del _pages[annotation_id]
        logger.info("Closed page for annotation %d", annotation_id)


async def _wait_for_render(page: Page) -> None:
    """Wait until the page body has visible content (JS frameworks finished rendering)."""
    try:
        await page.wait_for_function(
            "document.body && document.body.innerText.trim().length > 50",
            timeout=5_000,
        )
    except PlaywrightTimeoutError:
        pass  # take screenshot with whatever rendered so far


async def _wait_for_page(page: Page) -> None:
    """Wait after an action (click/scroll) for the page to settle."""
    try:
        await page.wait_for_load_state("networkidle", timeout=5_000)
    except PlaywrightTimeoutError:
        pass
    await asyncio.sleep(0.3)  # brief pause for JS re-renders after action


async def take_page_screenshot(page: Page) -> str:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = SCREENSHOTS_DIR / filename
    await _wait_for_page(page)
    await page.screenshot(path=str(filepath))
    return f"screenshots/{filename}"


async def perform_click(page: Page, x: int, y: int) -> None:
    await page.mouse.click(x, y)
    await _wait_for_page(page)


async def perform_scroll(page: Page, direction: str) -> None:
    if direction == "scroll_up":
        await page.mouse.wheel(0, -1000)
    else:
        await page.mouse.wheel(0, 1000)
    await _wait_for_page(page)
