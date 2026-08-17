"""
Integration tests that run the scanner against local fixture HTML pages.
Requires: playwright install chromium
"""
from __future__ import annotations

import pytest

from src.scanner.axe_runner import AxeRunner
from src.scanner.crawler import Crawler


@pytest.mark.integration
class TestCrawler:
    async def test_single_page_crawl(self, fixture_server):
        async with Crawler() as crawler:
            pages = await crawler.crawl(f"{fixture_server}/clean.html", max_pages=1)
        assert len(pages) == 1
        assert "clean.html" in pages[0]

    async def test_max_pages_respected(self, fixture_server):
        async with Crawler() as crawler:
            pages = await crawler.crawl(f"{fixture_server}/index.html", max_pages=2)
        assert len(pages) <= 2


@pytest.mark.integration
class TestAxeRunner:
    async def test_clean_page_has_no_violations(self, fixture_server):
        async with AxeRunner() as runner:
            result = await runner.scan_page(f"{fixture_server}/clean.html")
        assert result.violations == []
        assert result.passes > 0

    async def test_violations_page_has_violations(self, fixture_server):
        async with AxeRunner() as runner:
            result = await runner.scan_page(f"{fixture_server}/violations.html")
        assert len(result.violations) > 0

    async def test_missing_alt_detected(self, fixture_server):
        async with AxeRunner() as runner:
            result = await runner.scan_page(f"{fixture_server}/violations.html")
        rule_ids = {v.rule_id for v in result.violations}
        assert "image-alt" in rule_ids

    async def test_result_url_matches(self, fixture_server):
        url = f"{fixture_server}/clean.html"
        async with AxeRunner() as runner:
            result = await runner.scan_page(url)
        assert result.url == url
