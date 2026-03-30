import asyncio
import logging
import time
import uuid
from pathlib import Path

from playwright.async_api import Browser, Page, ViewportSize, async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("media/screenshots")
VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}

_playwright = None
_browser: Browser | None = None
_pages: dict[int, Page] = {}
_last_access: dict[int, float] = {}
_cleanup_task: asyncio.Task | None = None


def get_browser() -> Browser:
    """Return the shared browser instance (must be started first)."""
    assert _browser is not None, "Browser not started"
    return _browser


async def _cleanup_loop() -> None:
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            now = time.time()
            idle_threshold = 15 * 60  # 15 minutes
            
            # Find pages that haven't been accessed recently
            to_close = [ann_id for ann_id, last_time in _last_access.items() 
                        if now - last_time > idle_threshold]
            
            for ann_id in to_close:
                logger.info("Cleaning up idle page for annotation %d", ann_id)
                await close_page(ann_id)
        except asyncio.CancelledError:
            break
        except PlaywrightError as e:
            logger.error("Playwright error in browser cleanup loop: %s", e)


async def start_browser() -> None:
    global _playwright, _browser, _cleanup_task
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=True)
    _cleanup_task = asyncio.create_task(_cleanup_loop())
    logger.info("Browser started and cleanup task scheduled")


async def stop_browser() -> None:
    global _playwright, _browser, _cleanup_task
    
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        _cleanup_task = None
        
    if _browser:
        await _browser.close()
        _browser = None
        
    if _playwright:
        await _playwright.stop()
        _playwright = None
        
    logger.info("Browser and playwright stopped")


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
    
    _last_access[annotation_id] = time.time()
    return _pages[annotation_id]


async def close_page(annotation_id: int) -> None:
    if annotation_id in _pages:
        await _pages[annotation_id].close()
        del _pages[annotation_id]
        if annotation_id in _last_access:
            del _last_access[annotation_id]
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
