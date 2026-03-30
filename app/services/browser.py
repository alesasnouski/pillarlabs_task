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


class ScreenshotError(Exception):
    pass


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._pages: dict[int, Page] = {}
        self._last_access: dict[int, float] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def _cleanup_loop(self) -> None:
        """Background task to periodically close idle pages to prevent memory leaks."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = time.time()
                idle_threshold = 15 * 60  # 15 minutes

                # Find pages that haven't been accessed recently
                to_close = [
                    ann_id for ann_id, last_time in self._last_access.items() if now - last_time > idle_threshold
                ]

                for ann_id in to_close:
                    logger.info("Cleaning up idle page for annotation %d", ann_id)
                    await self.close_page(ann_id)
            except asyncio.CancelledError:
                break
            except PlaywrightError as e:
                logger.error("Playwright error in browser cleanup loop: %s", e)

    async def start(self) -> None:
        """Launch the global Playwright browser instance and start the background cleanup task."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Browser started and cleanup task scheduled")

    async def stop(self) -> None:
        """Gracefully stop the background cleanup task and terminate the Playwright session."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Browser and playwright stopped")

    async def get_or_create_page(self, annotation_id: int, url: str) -> Page:
        """Retrieve an existing page/tab for the given annotation ID, or spawn a new one and navigate to the URL."""
        if annotation_id not in self._pages:
            assert self._browser is not None, "Browser not started"
            page = await self._browser.new_page(viewport=VIEWPORT)
            await page.goto(url, wait_until="load", timeout=30_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=5_000)
            except PlaywrightTimeoutError:
                pass
            await self._wait_for_render(page)
            self._pages[annotation_id] = page
            logger.info("Created page for annotation %d", annotation_id)

        self._last_access[annotation_id] = time.time()
        return self._pages[annotation_id]

    async def close_page(self, annotation_id: int) -> None:
        """Close the page/tab associated with the given annotation ID and clean up references."""
        if annotation_id in self._pages:
            await self._pages[annotation_id].close()
            del self._pages[annotation_id]
            if annotation_id in self._last_access:
                del self._last_access[annotation_id]
            logger.info("Closed page for annotation %d", annotation_id)

    async def _wait_for_render(self, page: Page) -> None:
        """Wait until the page body has visible content (JS frameworks finished rendering)."""
        try:
            await page.wait_for_function(
                "document.body && document.body.innerText.trim().length > 50",
                timeout=5_000,
            )
        except PlaywrightTimeoutError:
            pass  # take screenshot with whatever rendered so far

    async def _wait_for_page(self, page: Page) -> None:
        """Wait after an action (click/scroll) for the page to settle."""
        try:
            await page.wait_for_load_state("networkidle", timeout=5_000)
        except PlaywrightTimeoutError:
            pass
        await asyncio.sleep(0.3)  # brief pause for JS re-renders after action

    async def take_page_screenshot(self, page: Page) -> str:
        """Capture and save a full-viewport screenshot for an active session page."""
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        filepath = SCREENSHOTS_DIR / filename
        await self._wait_for_page(page)
        await page.screenshot(path=str(filepath))
        return f"screenshots/{filename}"

    async def perform_click(self, page: Page, x: int, y: int) -> None:
        """Simulate a mouse click at specific coordinates and wait for the page to settle."""
        await page.mouse.click(x, y)
        await self._wait_for_page(page)

    async def perform_type(self, page: Page, text: str) -> None:
        """Type the given text using the keyboard on the currently focused element."""
        # We assume the user has already clicked on the input field before typing
        await page.keyboard.type(text)
        await self._wait_for_page(page)

    async def perform_scroll(self, page: Page, direction: str) -> None:
        """Simulate a mouse wheel scroll event up or down and wait for the page to settle."""
        if direction == "scroll_up":
            await page.mouse.wheel(0, -1000)
        else:
            await page.mouse.wheel(0, 1000)
        await self._wait_for_page(page)

    async def take_screenshot(self, url: str) -> str:
        """Take a preview screenshot using the persistent browser."""
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        filepath = SCREENSHOTS_DIR / filename

        try:
            assert self._browser is not None, "Browser not started yet"
            page = await self._browser.new_page(viewport=VIEWPORT)
            try:
                await page.goto(url, wait_until="load", timeout=15_000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5_000)
                except PlaywrightTimeoutError:
                    pass
                await self._wait_for_render(page)
                await page.screenshot(path=str(filepath))
            finally:
                await page.close()
        except AssertionError as e:
            raise ScreenshotError(str(e))
        except PlaywrightTimeoutError:
            raise ScreenshotError(f"Page timed out loading: {url}")
        except PlaywrightError as e:
            logger.exception("Screenshot failed for %s", url)
            raise ScreenshotError(str(e)) from e

        return f"screenshots/{filename}"


# Global instance
browser_manager = BrowserManager()


def get_browser_manager() -> BrowserManager:
    """FastAPI Dependency for dependency injection."""
    return browser_manager
