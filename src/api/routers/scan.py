from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.api.models import ScanRequest, ScanResponse, ScanStatus
from src.api.services.scanner_service import run_scan
from src.storage.scan_store import ScanStore

router = APIRouter(tags=["scan"])


@router.post("/scan", response_model=ScanResponse, status_code=202)
async def create_scan(
    req: ScanRequest,
    background_tasks: BackgroundTasks,
) -> ScanResponse:
    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    record = ScanResponse(
        id=scan_id,
        status=ScanStatus.queued,
        request=req,
        created_at=now,
    )
    await ScanStore.save(record)
    background_tasks.add_task(_execute, scan_id, req)
    return record


@router.get("/scan/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str) -> ScanResponse:
    record = await ScanStore.get(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return record


async def _execute(scan_id: str, req: ScanRequest) -> None:
    record = await ScanStore.get(scan_id)
    if record is None:
        return

    record.status = ScanStatus.running
    await ScanStore.save(record)

    try:
        pages = await run_scan(str(req.url), req.max_pages, req.tags)
        record.pages = pages
        record.status = ScanStatus.complete
        record.summary = _summarise(record)
    except Exception as exc:  # noqa: BLE001
        record.status = ScanStatus.failed
        record.error = str(exc)
    finally:
        record.finished_at = datetime.now(timezone.utc)
        await ScanStore.save(record)


def _summarise(record: ScanResponse) -> dict:
    from src.api.models import Severity

    counts: dict[str, int] = {s.value: 0 for s in Severity}
    total_violations = 0
    for page in record.pages:
        for v in page.violations:
            counts[v.severity.value] += 1
            total_violations += 1

    return {
        "total_violations": total_violations,
        "by_severity": counts,
        "pages_scanned": len(record.pages),
    }
