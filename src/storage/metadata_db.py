"""Metadata database — ingestion and pipeline run tracking."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from common.config import load_settings, resolve_path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    sources TEXT,
    record_count INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running',
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    counts TEXT,
    PRIMARY KEY (run_id, stage)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started
    ON ingestion_runs (started_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_id
    ON pipeline_runs (run_id);
"""


class MetadataDB:
    """SQLite-backed store for ingestion and pipeline run metadata."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            settings = load_settings()
            db_path = resolve_path(settings.paths.metadata_db)
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _dump_json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def start_ingestion_run(
        self,
        run_id: str,
        sources: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO ingestion_runs (run_id, started_at, sources, status, metadata)
                VALUES (?, ?, ?, 'running', ?)
                """,
                (
                    run_id,
                    self._now_iso(),
                    json.dumps(sources or []),
                    self._dump_json(metadata),
                ),
            )

    def finish_ingestion_run(
        self,
        run_id: str,
        record_count: int,
        status: str = "completed",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE ingestion_runs
                SET finished_at = ?, record_count = ?, status = ?,
                    metadata = COALESCE(?, metadata)
                WHERE run_id = ?
                """,
                (
                    self._now_iso(),
                    record_count,
                    status,
                    self._dump_json(metadata),
                    run_id,
                ),
            )

    def start_pipeline_stage(
        self,
        run_id: str,
        stage: str,
        counts: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pipeline_runs
                (run_id, stage, started_at, status, counts)
                VALUES (?, ?, ?, 'running', ?)
                """,
                (run_id, stage, self._now_iso(), self._dump_json(counts)),
            )

    def finish_pipeline_stage(
        self,
        run_id: str,
        stage: str,
        status: str = "completed",
        counts: dict[str, Any] | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = ?, status = ?,
                    counts = COALESCE(?, counts)
                WHERE run_id = ? AND stage = ?
                """,
                (self._now_iso(), status, self._dump_json(counts), run_id, stage),
            )

    def get_ingestion_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM ingestion_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_ingestion_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM ingestion_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
