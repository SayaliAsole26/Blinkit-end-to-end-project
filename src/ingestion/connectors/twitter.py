"""Twitter/X connector — manual CSV fallback."""

from __future__ import annotations

from pathlib import Path

from ingestion.connectors.base import resolve_sample_path
from ingestion.connectors.csv_connector import CSVConnector


class TwitterConnector(CSVConnector):
    platform = "twitter"

    def __init__(self, csv_path: Path | None = None) -> None:
        super().__init__(
            csv_path=csv_path or resolve_sample_path("twitter.csv"),
            platform_override="twitter",
        )
