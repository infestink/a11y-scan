from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, async_playwright

from src.api.models import NodeDetail, PageResult, Severity, Violation
from src.scanner.severity import map_severity

# axe-core CDN — pinned version, overridable via env
_AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/{version}/axe.min.js"
_AXE_VERSION = os.getenv("AXE_VERSION", "4.9.1")
_AXE_LOCAL = os.getenv("AXE_LOCAL_PATH", "")

_AXE_SCRIPT: str | None = None


def _load_axe_script() -> str:
    global _AXE_SCRIPT
    if _AXE_SCRIPT is not None:
        return _AXE_SCRIPT

    if _AXE_LOCAL:
        _AXE_SCRIPT = Path(_AXE_LOCAL).read_text(encoding="utf-8")
    else:
        import urllib.request
        url = _AXE_CDN.format(version=_AXE_VERSION)
        with urllib.request.urlopen(url, timeout=20) as resp:
            _AXE_SCRIPT = resp.read().decode("utf-8")

    return _AXE_SCRIPT


class AxeRunner:
    """Injects axe-core into each page, runs it, and parses violations."""

    def __init__(self, tags: list[str] | None = None) -> None:
        self._tags = tags or ["wcag2a", "wcag2aa", "wcag21aa"]
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._playwright = None

    async def __aenter__(self) -> "AxeRunner":
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

    async def scan_page(self, url: str) -> PageResult:
        if self._context is None:
            raise RuntimeError("AxeRunner must be used as an async context manager")

        axe_js = _load_axe_script()
        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            await page.add_script_tag(content=axe_js)

            run_options = json.dumps({"runOnly": {"type": "tag", "values": self._tags}})
            raw: dict[str, Any] = await page.evaluate(
                f"() => axe.run(document, {run_options})"
            )
        finally:
            await page.close()

        return _parse_result(url, raw)


def _parse_result(url: str, raw: dict[str, Any]) -> PageResult:
    violations: list[Violation] = []

    for v in raw.get("violations", []):
        nodes = [
            NodeDetail(
                html=n.get("html", ""),
                target=n.get("target", []),
                failure_summary=n.get("failureSummary"),
            )
            for n in v.get("nodes", [])
        ]
        impact = v.get("impact") or "minor"
        violations.append(
            Violation(
                rule_id=v["id"],
                description=v.get("description", ""),
                help_url=v.get("helpUrl", ""),
                severity=map_severity(v["id"], impact),
                impact=impact,
                nodes=nodes,
            )
        )

    return PageResult(
        url=url,
        violations=violations,
        passes=len(raw.get("passes", [])),
        incomplete=len(raw.get("incomplete", [])),
        inapplicable=len(raw.get("inapplicable", [])),
        scanned_at=datetime.now(timezone.utc),
    )
