from __future__ import annotations

import os
from collections import deque
from urllib.parse import urljoin, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class Crawler:
    """
    Discovers pages starting from a seed URL via BFS link-following.
    Stays within the same origin; respects max_pages cap.
    """

    def __init__(self) -> None:
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._playwright = None

    async def __aenter__(self) -> "Crawler":
        self._playwright = await async_playwright().start()
        browser_type = os.getenv("BROWSER", "chromium")
        headless = os.getenv("HEADLESS", "true").lower() != "false"
        launcher = getattr(self._playwright, browser_type)
        self._browser = await launcher.launch(headless=headless)
        self._context = await self._browser.new_context()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def crawl(self, seed_url: str, max_pages: int = 1) -> list[str]:
        if self._context is None:
            raise RuntimeError("Crawler must be used as an async context manager")

        origin = _origin(seed_url)
        visited: set[str] = set()
        queue: deque[str] = deque([seed_url])
        ordered: list[str] = []

        wait_ms = int(os.getenv("DEFAULT_WAIT_MS", "500"))

        while queue and len(ordered) < max_pages:
            url = queue.popleft()
            normalised = _normalise(url)
            if normalised in visited:
                continue
            visited.add(normalised)

            page: Page = await self._context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                if wait_ms:
                    await page.wait_for_timeout(wait_ms)
                ordered.append(page.url)

                if len(ordered) < max_pages:
                    links = await page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.href)",
                    )
                    for link in links:
                        if _origin(link) == origin and _normalise(link) not in visited:
                            queue.append(link)
            except Exception:  # noqa: BLE001
                pass
            finally:
                await page.close()

        return ordered


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _normalise(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")
