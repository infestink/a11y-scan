from __future__ import annotations

from src.api.models import PageResult
from src.scanner.axe_runner import AxeRunner
from src.scanner.crawler import Crawler
from src.scanner.severity import map_severity


async def run_scan(
    url: str,
    max_pages: int,
    tags: list[str],
) -> list[PageResult]:
    async with Crawler() as crawler:
        pages = await crawler.crawl(url, max_pages=max_pages)

    results: list[PageResult] = []
    async with AxeRunner(tags=tags) as runner:
        for page_url in pages:
            page_result = await runner.scan_page(page_url)
            # Enrich severity using our mapping layer
            for violation in page_result.violations:
                violation.severity = map_severity(violation.rule_id, violation.impact)
            results.append(page_result)

    return results
