"""Google Play Store review connector — CSV import (primary)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.connectors.base import BaseConnector, resolve_sample_path, with_exponential_backoff


class PlayStoreConnector(BaseConnector):
    """
    Import Blinkit Play Store reviews from CSV export.

    Expected columns (flexible):
      review_text | text | content
      score | rating
      at | created_at | date
      review_url | url
    """

    platform = "play_store"

    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or resolve_sample_path("play_store.csv")

    def fetch(self) -> list[dict[str, Any]]:
        def _load() -> list[dict[str, Any]]:
            if not self.csv_path.exists():
                return []
            rows: list[dict[str, Any]] = []
            with self.csv_path.open(encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    text = (
                        row.get("review_text")
                        or row.get("text")
                        or row.get("content")
                        or ""
                    )
                    rating_raw = row.get("score") or row.get("rating") or ""
                    rating = int(rating_raw) if str(rating_raw).strip() else None
                    date_raw = row.get("at") or row.get("created_at") or row.get("date")
                    url = (
                        row.get("review_url")
                        or row.get("url")
                        or f"https://play.google.com/review/{i}"
                    )
                    user = row.get("user_name") or row.get("author") or "anonymous"
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
                                "user_name": user,
                                "source": "play_store_csv",
                            },
                        }
                    )
            return rows

        return with_exponential_backoff(_load, max_retries=3)
