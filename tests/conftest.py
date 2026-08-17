from __future__ import annotations

import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.api.main import app
from src.storage.scan_store import ScanStore


# ---------------------------------------------------------------------------
# Async event loop
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# In-memory DB for API / unit tests
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=False)
async def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    await ScanStore.initialise(db_path)
    yield
    await ScanStore.close()


# ---------------------------------------------------------------------------
# FastAPI test clients
# ---------------------------------------------------------------------------

@pytest.fixture
def sync_client(db):
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Local fixture HTML server (integration tests)
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "html"


@pytest.fixture(scope="session")
def fixture_server():
    """Serve fixtures/html/ over HTTP on a random port."""
    server = HTTPServer(("127.0.0.1", 0), _FixtureHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


class _FixtureHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FIXTURES_DIR), **kwargs)

    def log_message(self, *args):  # silence request logs in test output
        pass
