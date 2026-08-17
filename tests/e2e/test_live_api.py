"""
End-to-end tests that drive the live API against a real running server.
Run with: pytest -m e2e --base-url=http://localhost:8000
Requires a running uvicorn instance and network access.
"""
from __future__ import annotations

import time

import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture
def live_client():
    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        yield c


@pytest.mark.e2e
class TestE2EScan:
    def test_health(self, live_client):
        resp = live_client.get("/healthz")
        assert resp.status_code == 200

    def test_full_scan_flow(self, live_client):
        resp = live_client.post(
            "/api/v1/scan",
            json={"url": "https://www.w3.org/WAI/demos/bad/before/home.html", "max_pages": 1},
        )
        assert resp.status_code == 202
        scan_id = resp.json()["id"]

        for _ in range(60):
            poll = live_client.get(f"/api/v1/scan/{scan_id}")
            assert poll.status_code == 200
            status = poll.json()["status"]
            if status in ("complete", "failed"):
                break
            time.sleep(2)

        final = live_client.get(f"/api/v1/scan/{scan_id}").json()
        assert final["status"] == "complete"
        assert final["summary"]["total_violations"] >= 0

    def test_violations_have_severity(self, live_client):
        resp = live_client.post(
            "/api/v1/scan",
            json={"url": "https://www.w3.org/WAI/demos/bad/before/home.html", "max_pages": 1},
        )
        scan_id = resp.json()["id"]

        for _ in range(60):
            poll = live_client.get(f"/api/v1/scan/{scan_id}")
            if poll.json()["status"] in ("complete", "failed"):
                break
            time.sleep(2)

        data = live_client.get(f"/api/v1/scan/{scan_id}").json()
        for page in data["pages"]:
            for v in page["violations"]:
                assert v["severity"] in ("critical", "serious", "advisory")
