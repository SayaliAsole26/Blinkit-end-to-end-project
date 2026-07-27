"""CSV import connector — manual corpus fallback for all sources."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.connectors.base import BaseConnector


def _parse_datetime(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


class CSVConnector(BaseConnector):
    """
    Read a normalized manual corpus CSV.

    Required columns: platform, raw_text, created_at, url
    Optional: rating, language, metadata (JSON string)
    """

    def __init__(
        self,
        csv_path: Path,
        platform_override: str | None = None,
    ) -> None:
        self.csv_path = csv_path
        self.platform_override = platform_override
        self.platform = platform_override or "forum"

    def fetch(self) -> list[dict[str, Any]]:
        if not self.csv_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.csv_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                platform = self.platform_override or row.get("platform", "forum")
                rating_raw = row.get("rating", "").strip()
                rating = int(rating_raw) if rating_raw else None
                metadata_raw = row.get("metadata", "").strip()
                metadata: dict[str, Any] = {}
                if metadata_raw:
                    metadata = json.loads(metadata_raw)
                rows.append(
                    {
                        "platform": platform,
                        "raw_text": row["raw_text"],
                        "rating": rating,
                        "created_at": _parse_datetime(row["created_at"]),
                        "url": row["url"],
                        "language": row.get("language") or None,
                        "metadata": metadata,
                        "source_file": str(self.csv_path.name),
                    }
                )
        return rows
