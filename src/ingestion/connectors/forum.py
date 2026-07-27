"""Forum/Quora connector — manual CSV fallback."""

from __future__ import annotations

from pathlib import Path

from ingestion.connectors.base import resolve_sample_path
from ingestion.connectors.csv_connector import CSVConnector


class ForumConnector(CSVConnector):
    platform = "forum"

    def __init__(self, csv_path: Path | None = None) -> None:
        super().__init__(
            csv_path=csv_path or resolve_sample_path("forum.csv"),
            platform_override="forum",
        )
