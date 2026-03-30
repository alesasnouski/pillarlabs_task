import logging
import uuid
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("media/screenshots")
VIEWPORT = {"width": 1920, "height": 1080}


class ScreenshotError(Exception):
    pass


async def take_screenshot(url: str) -> str:
    """Open URL in headless browser, take screenshot, return file path relative to media root."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = SCREENSHOTS_DIR / filename

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(viewport=VIEWPORT)
                await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                await page.screenshot(path=str(filepath))
            finally:
                await browser.close()
    except PlaywrightTimeoutError:
        raise ScreenshotError(f"Page timed out loading: {url}")
    except PlaywrightError as e:
        logger.exception("Screenshot failed for %s", url)
        raise ScreenshotError(str(e)) from e

    return f"screenshots/{filename}"
