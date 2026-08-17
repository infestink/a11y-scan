from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import aiosqlite

from src.api.models import ScanResponse

_DB_PATH = os.getenv("DB_PATH", "./data/scans.db")
_conn: aiosqlite.Connection | None = None


class ScanStore:
    @staticmethod
    async def initialise(db_path: str | None = None) -> None:
        global _conn
        path = db_path or _DB_PATH
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        _conn = await aiosqlite.connect(path)
        await _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id          TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                finished_at TEXT,
                status      TEXT NOT NULL,
                payload     TEXT NOT NULL
            )
            """
        )
        await _conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON scans(url)")
        await _conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON scans(created_at)")
        await _conn.commit()

    @staticmethod
    async def close() -> None:
        global _conn
        if _conn is not None:
            await _conn.close()
            _conn = None

    @staticmethod
    async def save(record: ScanResponse) -> None:
        if _conn is None:
            raise RuntimeError("ScanStore not initialised")
        payload = record.model_dump_json()
        await _conn.execute(
            """
            INSERT INTO scans (id, url, created_at, finished_at, status, payload)
            VALUES (:id, :url, :created_at, :finished_at, :status, :payload)
            ON CONFLICT(id) DO UPDATE SET
                finished_at = excluded.finished_at,
                status      = excluded.status,
                payload     = excluded.payload
            """,
            {
                "id": record.id,
                "url": str(record.request.url),
                "created_at": record.created_at.isoformat(),
                "finished_at": record.finished_at.isoformat() if record.finished_at else None,
                "status": record.status.value,
                "payload": payload,
            },
        )
        await _conn.commit()

    @staticmethod
    async def get(scan_id: str) -> ScanResponse | None:
        if _conn is None:
            raise RuntimeError("ScanStore not initialised")
        async with _conn.execute(
            "SELECT payload FROM scans WHERE id = ?", (scan_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return ScanResponse.model_validate_json(row[0])

    @staticmethod
    async def latest_for_url(url: str) -> ScanResponse | None:
        """Return the most recent *complete* scan for a given URL."""
        if _conn is None:
            raise RuntimeError("ScanStore not initialised")
        async with _conn.execute(
            """
            SELECT payload FROM scans
            WHERE url = ? AND status = 'complete'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (url,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return ScanResponse.model_validate_json(row[0])
