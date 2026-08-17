from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api.routers import scan as scan_router
from src.storage.scan_store import ScanStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await ScanStore.initialise()
    yield
    await ScanStore.close()


app = FastAPI(
    title="a11y-scan",
    description="Automated accessibility scanner powered by axe-core + Playwright",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(scan_router.router, prefix="/api/v1")


@app.get("/healthz", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
