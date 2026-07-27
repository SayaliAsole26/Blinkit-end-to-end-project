"""Orchestrator for Phase 2 — Filter → Preprocess → Clean → Embed."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from common.config import AppSettings, load_settings, resolve_path
from common.logging import get_logger, log_event
from ingestion.raw_store import RawStore
from pipeline.clean import CleanModule
from pipeline.embed import EmbedModule, Embedder
from pipeline.filter import FilterModule, write_filter_audit
from pipeline.preprocess import PreprocessModule
from storage.embedding_cache import EmbeddingCache
from storage.metadata_db import MetadataDB
from storage.vector_store import VectorStore
from models.records import CleanSegment

logger = get_logger(__name__)


@dataclass
class CleanEmbedResult:
    pipeline_run_id: str
    filter_summary: dict = field(default_factory=dict)
    preprocess_summary: dict = field(default_factory=dict)
    clean_summary: dict = field(default_factory=dict)
    embed_summary: dict = field(default_factory=dict)
    segments_path: str | None = None
    filter_audit_path: str | None = None
    total_input_records: int = 0

    def to_dict(self) -> dict:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_input_records": self.total_input_records,
            "filter": self.filter_summary,
            "preprocess": self.preprocess_summary,
            "clean": self.clean_summary,
            "embed": self.embed_summary,
            "segments_path": self.segments_path,
            "filter_audit_path": self.filter_audit_path,
        }


class CleanEmbedPipeline:
    """Run stages 1–4 on raw store records."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        embedder: Embedder | None = None,
        cache: EmbeddingCache | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.filter_mod = FilterModule(self.settings)
        self.preprocess_mod = PreprocessModule(self.settings)
        self.clean_mod = CleanModule(self.settings)
        self.embed_mod = EmbedModule(
            self.settings,
            cache=cache,
            vector_store=vector_store,
            embedder=embedder,
        )
        self.raw_store = RawStore()
        self.metadata_db = MetadataDB()

    def run(
        self,
        pipeline_run_id: str,
        ingestion_run_id: str | None = None,
        *,
        persist_segments: bool = True,
    ) -> CleanEmbedResult:
        records = list(self.raw_store.read_ingestion(ingestion_run_id))
        result = CleanEmbedResult(
            pipeline_run_id=pipeline_run_id,
            total_input_records=len(records),
        )

        self.metadata_db.start_pipeline_stage(pipeline_run_id, "clean_embed")
        log_event(
            logger,
            logging.INFO,
            "clean_embed started",
            run_id=pipeline_run_id,
            stage="clean_embed",
            counts={"input_records": len(records)},
        )

        try:
            filter_result = self.filter_mod.run(records)
            result.filter_summary = filter_result.summary()
            log_event(
                logger,
                logging.INFO,
                "filter complete",
                run_id=pipeline_run_id,
                stage="filter",
                counts=result.filter_summary,
            )
            audit_path = write_filter_audit(filter_result, pipeline_run_id)
            result.filter_audit_path = str(audit_path)

            preprocess_result = self.preprocess_mod.run(filter_result.records)
            result.preprocess_summary = preprocess_result.summary()
            log_event(
                logger,
                logging.INFO,
                "preprocess complete",
                run_id=pipeline_run_id,
                stage="preprocess",
                counts=result.preprocess_summary,
            )

            self.clean_mod.filtered_by_id = {
                r.record_id: r for r in filter_result.records
            }
            clean_result = self.clean_mod.run(
                preprocess_result.segments,
                filtered_records=filter_result.records,
            )
            result.clean_summary = clean_result.summary()
            log_event(
                logger,
                logging.INFO,
                "clean complete",
                run_id=pipeline_run_id,
                stage="clean",
                counts=result.clean_summary,
            )

            if persist_segments:
                result.segments_path = str(
                    self._write_segments(clean_result.segments, pipeline_run_id)
                )

            embed_result = self.embed_mod.run(clean_result.segments)
            result.embed_summary = embed_result.summary()
            log_event(
                logger,
                logging.INFO,
                "embed complete",
                run_id=pipeline_run_id,
                stage="embed",
                counts=result.embed_summary,
            )

            self.metadata_db.finish_pipeline_stage(
                pipeline_run_id,
                "clean_embed",
                status="completed",
                counts=result.to_dict(),
            )
        except Exception:
            self.metadata_db.finish_pipeline_stage(
                pipeline_run_id,
                "clean_embed",
                status="failed",
            )
            raise

        summary_path = resolve_path(self.settings.paths.processed_data) / (
            f"clean_embed_summary_{pipeline_run_id}.json"
        )
        summary_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        return result

    def _write_segments(
        self,
        segments: list[CleanSegment],
        pipeline_run_id: str,
    ) -> Path:
        out_dir = resolve_path(f"{self.settings.paths.processed_data}/segments")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"segments_{pipeline_run_id}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for seg in segments:
                f.write(seg.model_dump_json())
                f.write("\n")
        return path
