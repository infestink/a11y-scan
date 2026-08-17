from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from src.api.models import PageResult, ScanStatus


@pytest.mark.api
class TestHealthEndpoint:
    def test_health_ok(self, sync_client):
        resp = sync_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.api
class TestCreateScan:
    def test_returns_202(self, sync_client):
        with patch("src.api.routers.scan.run_scan", new_callable=AsyncMock, return_value=[]):
            resp = sync_client.post("/api/v1/scan", json={"url": "https://example.com"})
        assert resp.status_code == 202

    def test_response_has_id(self, sync_client):
        with patch("src.api.routers.scan.run_scan", new_callable=AsyncMock, return_value=[]):
            resp = sync_client.post("/api/v1/scan", json={"url": "https://example.com"})
        assert "id" in resp.json()

    def test_invalid_url_rejected(self, sync_client):
        resp = sync_client.post("/api/v1/scan", json={"url": "not-a-url"})
        assert resp.status_code == 422

    def test_max_pages_zero_rejected(self, sync_client):
        resp = sync_client.post("/api/v1/scan", json={"url": "https://example.com", "max_pages": 0})
        assert resp.status_code == 422


@pytest.mark.api
class TestGetScan:
    def test_not_found(self, sync_client):
        resp = sync_client.get("/api/v1/scan/nonexistent-id")
        assert resp.status_code == 404

    def test_retrieve_created_scan(self, sync_client):
        with patch("src.api.routers.scan.run_scan", new_callable=AsyncMock, return_value=[]):
            post_resp = sync_client.post("/api/v1/scan", json={"url": "https://example.com"})
        scan_id = post_resp.json()["id"]

        # Poll briefly — background task may complete very quickly in tests
        for _ in range(10):
            get_resp = sync_client.get(f"/api/v1/scan/{scan_id}")
            assert get_resp.status_code == 200
            if get_resp.json()["status"] in (ScanStatus.complete, ScanStatus.failed):
                break
            time.sleep(0.1)

        assert get_resp.json()["id"] == scan_id
