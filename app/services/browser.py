import logging
import uuid
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.services.browser_session import VIEWPORT, _wait_for_render, get_browser

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path("media/screenshots")


class ScreenshotError(Exception):
    pass


async def take_screenshot(url: str) -> str:
    """Take a preview screenshot using the persistent browser."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = SCREENSHOTS_DIR / filename

    try:
        browser = get_browser()
        page = await browser.new_page(viewport=VIEWPORT)
        try:
            await page.goto(url, wait_until="load", timeout=15_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=5_000)
            except PlaywrightTimeoutError:
                pass
            await _wait_for_render(page)
            await page.screenshot(path=str(filepath))
        finally:
            await page.close()
    except AssertionError:
        raise ScreenshotError("Browser not started yet")
    except PlaywrightTimeoutError:
        raise ScreenshotError(f"Page timed out loading: {url}")
    except PlaywrightError as e:
        logger.exception("Screenshot failed for %s", url)
        raise ScreenshotError(str(e)) from e

    return f"screenshots/{filename}"
