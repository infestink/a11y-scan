"""CLI entry-point for the nightly scan workflow."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import yaml

from src.api.models import ScanRequest, ScanResponse, ScanStatus
from src.api.services.scanner_service import run_scan
from src.reporting.report_builder import build_html_report, build_json_report
from src.storage.scan_store import ScanStore


async def main(
    targets_file: str,
    db_path: str,
    reports_dir: str,
    threshold: int,
) -> int:
    targets = _load_targets(targets_file)
    await ScanStore.initialise(db_path)

    new_criticals = 0
    exit_code = 0

    Path(reports_dir).mkdir(parents=True, exist_ok=True)

    for target in targets:
        url: str = target["url"]
        label: str = target.get("label", url)
        max_pages: int = target.get("max_pages", 1)

        print(f"[scan] {label} ({url}) …", flush=True)
        req = ScanRequest(url=url, max_pages=max_pages)  # type: ignore[arg-type]

        try:
            pages = await run_scan(url, max_pages, req.tags)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}", flush=True)
            continue

        from datetime import datetime, timezone
        import uuid

        now = datetime.now(timezone.utc)
        record = ScanResponse(
            id=str(uuid.uuid4()),
            status=ScanStatus.complete,
            request=req,
            created_at=now,
            finished_at=now,
            pages=pages,
        )

        prev = await ScanStore.latest_for_url(url)
        delta = _critical_delta(record, prev)
        new_criticals += max(0, delta)

        await ScanStore.save(record)

        stem = url.replace("://", "_").replace("/", "_").replace(".", "_")[:60]
        build_json_report(record, Path(reports_dir) / f"{stem}.json")
        build_html_report(record, Path(reports_dir) / f"{stem}.html")

        crit = sum(1 for p in pages for v in p.violations if v.severity.value == "critical")
        print(f"  violations: {sum(len(p.violations) for p in pages)}  critical: {crit}  delta: {delta:+d}")

    if new_criticals > threshold:
        print(
            f"\nREGRESSION: {new_criticals} new critical violations exceed threshold {threshold}",
            file=sys.stderr,
        )
        _maybe_notify(new_criticals, threshold)
        exit_code = 1

    await ScanStore.close()
    return exit_code


def _load_targets(path: str) -> list[dict]:
    with open(path) as fh:
        data = yaml.safe_load(fh)
    return data.get("targets", [])


def _critical_delta(current: ScanResponse, previous: ScanResponse | None) -> int:
    def count_critical(r: ScanResponse) -> int:
        return sum(1 for p in r.pages for v in p.violations if v.severity.value == "critical")

    curr = count_critical(current)
    if previous is None:
        return curr
    return curr - count_critical(previous)


def _maybe_notify(new_criticals: int, threshold: int) -> None:
    webhook = os.getenv("NOTIFY_WEBHOOK_URL", "")
    if not webhook:
        return
    import urllib.request

    payload = json.dumps({
        "text": f":rotating_light: a11y-scan regression: {new_criticals} new critical violations (threshold: {threshold})",
    }).encode()
    try:
        req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:  # noqa: BLE001
        print(f"  warning: webhook notification failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nightly a11y scan runner")
    parser.add_argument("--targets", default="targets.yaml")
    parser.add_argument("--db", default="./data/scans.db")
    parser.add_argument("--reports-dir", default="./reports")
    parser.add_argument("--threshold", type=int, default=5)
    args = parser.parse_args()

    sys.exit(asyncio.run(main(args.targets, args.db, args.reports_dir, args.threshold)))
