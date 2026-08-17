from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


class ScanStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


class Severity(str, Enum):
    critical = "critical"
    serious = "serious"
    advisory = "advisory"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 1
    tags: list[str] = ["wcag2a", "wcag2aa", "wcag21aa"]

    @field_validator("max_pages")
    @classmethod
    def positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_pages must be >= 1")
        return v


# ---------------------------------------------------------------------------
# Violation / result fragments
# ---------------------------------------------------------------------------

class NodeDetail(BaseModel):
    html: str
    target: list[str]
    failure_summary: str | None = None


class Violation(BaseModel):
    rule_id: str
    description: str
    help_url: str
    severity: Severity
    impact: str
    nodes: list[NodeDetail]


class PageResult(BaseModel):
    url: str
    violations: list[Violation]
    passes: int
    incomplete: int
    inapplicable: int
    scanned_at: datetime


# ---------------------------------------------------------------------------
# Scan response
# ---------------------------------------------------------------------------

class ScanResponse(BaseModel):
    id: str
    status: ScanStatus
    request: ScanRequest
    created_at: datetime
    finished_at: datetime | None = None
    pages: list[PageResult] = []
    summary: dict[str, Any] = {}
    error: str | None = None
