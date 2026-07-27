"""Apple App Store review connector — CSV import (primary)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.connectors.base import BaseConnector, resolve_sample_path, with_exponential_backoff


class AppStoreConnector(BaseConnector):
    """
    Import Blinkit App Store reviews from CSV export.

    Expected columns:
      content | review_text
      rating | score
      updated | created_at | date
      link | url
    """

    platform = "app_store"

    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or resolve_sample_path("app_store.csv")

    def fetch(self) -> list[dict[str, Any]]:
        def _load() -> list[dict[str, Any]]:
            if not self.csv_path.exists():
                return []
            rows: list[dict[str, Any]] = []
            with self.csv_path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    text = row.get("content") or row.get("review_text") or ""
                    rating_raw = row.get("rating") or row.get("score") or ""
                    rating = int(rating_raw) if str(rating_raw).strip() else None
                    date_raw = row.get("updated") or row.get("created_at") or row.get("date")
                    url = row.get("link") or row.get("url") or f"https://apps.apple.com/review/{i}"
                    created_at = datetime.fromisoformat(
                        date_raw.replace("Z", "+00:00") if "Z" in date_raw else date_raw
                    )
                    rows.append(
                        {
                            "platform": self.platform,
                            "raw_text": text,
                            "rating": rating,
                            "created_at": created_at,
                            "url": url,
                            "metadata": {
                                "source": "app_store_csv",
                                "title": row.get("title"),
                            },
                        }
                    )
            return rows

        return with_exponential_backoff(_load, max_retries=3)
