"""SHA-256 keyed embedding cache for BGE vectors."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from common.config import load_settings, resolve_path


def cache_key(embed_text: str, model_version: str) -> str:
    payload = f"{model_version}|{embed_text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _pack_vector(values: list[float]) -> bytes:
    return struct.pack(f"{len(values)}f", *values)


def _unpack_vector(data: bytes) -> list[float]:
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


SCHEMA = """
CREATE TABLE IF NOT EXISTS embedding_cache (
    cache_key TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    embedding BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_embedding_cache_model
    ON embedding_cache (model_version);
"""


class EmbeddingCache:
    """SQLite cache: SHA-256(embed_text + model_version) → vector."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            settings = load_settings()
            db_path = resolve_path(settings.embedding.cache_path)
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get(self, embed_text: str, model_version: str) -> list[float] | None:
        key = cache_key(embed_text, model_version)
        with self.connection() as conn:
            row = conn.execute(
                "SELECT embedding FROM embedding_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return _unpack_vector(row[0])

    def get_many(
        self,
        embed_texts: list[str],
        model_version: str,
    ) -> dict[str, list[float] | None]:
        keys = [cache_key(t, model_version) for t in embed_texts]
        result: dict[str, list[float] | None] = {t: None for t in embed_texts}
        if not keys:
            return result
        placeholders = ",".join("?" * len(keys))
        with self.connection() as conn:
            rows = conn.execute(
                f"SELECT cache_key, embedding FROM embedding_cache WHERE cache_key IN ({placeholders})",
                keys,
            ).fetchall()
        key_to_vec = {r[0]: _unpack_vector(r[1]) for r in rows}
        for text, key in zip(embed_texts, keys, strict=True):
            result[text] = key_to_vec.get(key)
        return result

    def put(self, embed_text: str, model_version: str, vector: list[float]) -> None:
        key = cache_key(embed_text, model_version)
        now = datetime.now(timezone.utc).isoformat()
        blob = _pack_vector(vector)
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO embedding_cache
                (cache_key, model_version, dimensions, embedding, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key, model_version, len(vector), blob, now),
            )

    def put_many(
        self,
        items: list[tuple[str, list[float]]],
        model_version: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for embed_text, vector in items:
            key = cache_key(embed_text, model_version)
            rows.append((key, model_version, len(vector), _pack_vector(vector), now))
        with self.connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO embedding_cache
                (cache_key, model_version, dimensions, embedding, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

    def stats(self) -> dict:
        with self.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()[0]
        return {"cached_vectors": count, "path": str(self.db_path)}

    def clear(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM embedding_cache")
