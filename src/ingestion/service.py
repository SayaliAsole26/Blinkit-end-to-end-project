"""Ingestion orchestration — fetch, normalize, persist, audit."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from common.logging import log_event
from common.run_id import generate_run_id
from ingestion.connectors import ALL_SOURCES, get_connector
from ingestion.normalizer import normalize_batch
from ingestion.raw_store import RawStore
from models.records import UnifiedRecord
from storage.metadata_db import MetadataDB

logger = logging.getLogger(__name__)


@dataclass
class IngestionSummary:
    ingestion_run_id: str
    sources: list[str]
    fetched_by_source: dict[str, int] = field(default_factory=dict)
    written: int = 0
    skipped_duplicates: int = 0
    total_in_store: int = 0
    platform_counts: dict[str, int] = field(default_factory=dict)
    null_rating_count: int = 0
    null_rating_pct: float = 0.0
    date_range: dict[str, str | None] = field(default_factory=dict)
    fallback_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingestion_run_id": self.ingestion_run_id,
            "sources": self.sources,
            "fetched_by_source": self.fetched_by_source,
            "written": self.written,
            "skipped_duplicates": self.skipped_duplicates,
            "total_in_store": self.total_in_store,
            "platform_counts": self.platform_counts,
            "null_rating_count": self.null_rating_count,
            "null_rating_pct": round(self.null_rating_pct, 2),
            "date_range": self.date_range,
            "fallback_sources": self.fallback_sources,
        }


class IngestionService:
    """Coordinate connectors, normalizer, raw store, and metadata DB."""

    def __init__(
        self,
        raw_store: RawStore | None = None,
        metadata_db: MetadataDB | None = None,
    ) -> None:
        self.raw_store = raw_store or RawStore()
        self.metadata_db = metadata_db or MetadataDB()

    def ingest(
        self,
        source: str = "all",
        run_id: str | None = None,
    ) -> IngestionSummary:
        ingestion_run_id = run_id or generate_run_id("ingest")
        sources = ALL_SOURCES if source == "all" else [source]
        summary = IngestionSummary(ingestion_run_id=ingestion_run_id, sources=sources)

        self.metadata_db.start_ingestion_run(ingestion_run_id, sources=sources)
        log_event(logger, logging.INFO, "Ingestion started", run_id=ingestion_run_id, stage="ingest")

        all_records: list[UnifiedRecord] = []

        for src in sources:
            connector = get_connector(src)
            rows = connector.fetch_safe()
            summary.fetched_by_source[src] = len(rows)
            if rows and rows[0].get("metadata", {}).get("source", "").endswith("_csv"):
                summary.fallback_sources.append(src)
            normalized = normalize_batch(rows, ingestion_run_id)
            all_records.extend(normalized)
            log_event(
                logger,
                logging.INFO,
                f"Normalized {len(normalized)} records from {src}",
                run_id=ingestion_run_id,
                stage="ingest",
                counts={"source": src, "normalized": len(normalized)},
            )

        store_result = self.raw_store.write_batch(all_records, ingestion_run_id)
        summary.written = store_result.written
        summary.skipped_duplicates = store_result.skipped_duplicates
        summary.total_in_store = store_result.total_in_run

        self._compute_stats(summary, all_records)
        audit_path = self.raw_store.write_audit(ingestion_run_id, summary.to_dict())

        self.metadata_db.finish_ingestion_run(
            ingestion_run_id,
            record_count=summary.total_in_store,
            metadata={
                "audit_path": str(audit_path),
                **summary.to_dict(),
            },
        )

        log_event(
            logger,
            logging.INFO,
            "Ingestion completed",
            run_id=ingestion_run_id,
            stage="ingest",
            counts=summary.to_dict(),
        )
        return summary

    @staticmethod
    def _compute_stats(summary: IngestionSummary, records: list[UnifiedRecord]) -> None:
        if not records:
            summary.date_range = {"min": None, "max": None}
            return
        platform_counter = Counter(r.platform for r in records)
        summary.platform_counts = dict(platform_counter)
        null_rating = sum(1 for r in records if r.rating is None)
        summary.null_rating_count = null_rating
        summary.null_rating_pct = (null_rating / len(records)) * 100 if records else 0.0
        dates = [r.created_at for r in records]
        summary.date_range = {
            "min": min(dates).isoformat(),
            "max": max(dates).isoformat(),
        }
