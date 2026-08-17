from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.api.models import (
    NodeDetail,
    PageResult,
    ScanRequest,
    ScanResponse,
    ScanStatus,
    Severity,
    Violation,
)
from src.reporting.report_builder import build_html_report, build_json_report


def _make_record(tmp_path: Path) -> tuple[ScanResponse, Path]:
    now = datetime.now(timezone.utc)
    violation = Violation(
        rule_id="color-contrast",
        description="Elements must have sufficient color contrast",
        help_url="https://dequeuniversity.com/rules/axe/4.9/color-contrast",
        severity=Severity.serious,
        impact="serious",
        nodes=[NodeDetail(html="<p style='color:#ccc'>hi</p>", target=["p"])],
    )
    page = PageResult(
        url="http://example.com/",
        violations=[violation],
        passes=10,
        incomplete=1,
        inapplicable=2,
        scanned_at=now,
    )
    req = ScanRequest(url="http://example.com/", max_pages=1)  # type: ignore[arg-type]
    record = ScanResponse(
        id="test-id-001",
        status=ScanStatus.complete,
        request=req,
        created_at=now,
        finished_at=now,
        pages=[page],
    )
    return record, tmp_path


@pytest.mark.unit
class TestBuildJsonReport:
    def test_creates_file(self, tmp_path):
        record, _ = _make_record(tmp_path)
        out = tmp_path / "report.json"
        build_json_report(record, out)
        assert out.exists()

    def test_valid_json(self, tmp_path):
        record, _ = _make_record(tmp_path)
        out = tmp_path / "report.json"
        build_json_report(record, out)
        data = json.loads(out.read_text())
        assert data["id"] == "test-id-001"
        assert data["status"] == "complete"

    def test_violations_present(self, tmp_path):
        record, _ = _make_record(tmp_path)
        out = tmp_path / "report.json"
        build_json_report(record, out)
        data = json.loads(out.read_text())
        assert data["pages"][0]["violations"][0]["rule_id"] == "color-contrast"


@pytest.mark.unit
class TestBuildHtmlReport:
    def test_creates_file(self, tmp_path):
        record, _ = _make_record(tmp_path)
        out = tmp_path / "report.html"
        build_html_report(record, out)
        assert out.exists()

    def test_contains_url(self, tmp_path):
        record, _ = _make_record(tmp_path)
        out = tmp_path / "report.html"
        build_html_report(record, out)
        assert "example.com" in out.read_text()

    def test_contains_rule_id(self, tmp_path):
        record, _ = _make_record(tmp_path)
        out = tmp_path / "report.html"
        build_html_report(record, out)
        assert "color-contrast" in out.read_text()

    def test_no_violations_page(self, tmp_path):
        record, _ = _make_record(tmp_path)
        record.pages[0].violations = []
        out = tmp_path / "report.html"
        build_html_report(record, out)
        assert "No violations found" in out.read_text()
