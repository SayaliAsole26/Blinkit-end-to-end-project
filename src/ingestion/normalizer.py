"""Map source-native connector rows to UnifiedRecord."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.records import Platform, UnifiedRecord


def normalize_row(
    row: dict[str, Any],
    ingestion_run_id: str,
) -> UnifiedRecord:
    """Convert a connector dict into a validated UnifiedRecord."""
    platform: Platform = row["platform"]
    raw_text: str = row["raw_text"]  # verbatim — no strip
    created_at: datetime = row["created_at"]
    url: str = row["url"]
    rating = row.get("rating")
    language = row.get("language")
    metadata = dict(row.get("metadata") or {})

    if rating is None and platform in ("reddit", "forum", "twitter"):
        metadata.setdefault("rating_missing", True)

    metadata.setdefault("source_connector", platform)

    return UnifiedRecord.build(
        platform=platform,
        raw_text=raw_text,
        created_at=created_at,
        url=url,
        ingestion_run_id=ingestion_run_id,
        rating=rating,
        language=language,
        metadata=metadata,
    )


def normalize_batch(
    rows: list[dict[str, Any]],
    ingestion_run_id: str,
) -> list[UnifiedRecord]:
    """Normalize many rows; dedupe by record_id within batch."""
    seen: set[str] = set()
    records: list[UnifiedRecord] = []
    for row in rows:
        record = normalize_row(row, ingestion_run_id)
        if record.record_id in seen:
            continue
        seen.add(record.record_id)
        records.append(record)
    return records
