"""Orchestrator for Phase 4 — synthesize insight cards + validate."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from common.config import AppSettings, load_settings, resolve_path
from common.logging import get_logger, log_event
from models.insights import InsightCard
from pipeline.cluster_label import load_segments, resolve_segments_path
from pipeline.synthesize import (
    SynthesisModule,
    load_analyses,
    load_cluster_memberships,
    load_search_gap_themes,
)
from pipeline.validate import ValidationModule
from storage.metadata_db import MetadataDB

logger = get_logger(__name__)


@dataclass
class SynthesizeValidateResult:
    pipeline_run_id: str
    cluster_label_run_id: str
    segments_run_id: str
    synthesis: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    insights_path: str | None = None
    validation_path: str | None = None
    insight_cards: list[InsightCard] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "cluster_label_run_id": self.cluster_label_run_id,
            "segments_run_id": self.segments_run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "synthesis": self.synthesis,
            "validation": self.validation,
            "insights_path": self.insights_path,
            "validation_path": self.validation_path,
        }


class SynthesizeValidatePipeline:
    """Run stages 10–11: insight synthesis + validation."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        groq_client=None,
    ) -> None:
        self.settings = settings or load_settings()
        self.synthesis_mod = SynthesisModule(self.settings)
        self.validation_mod = ValidationModule(self.settings, groq_client=groq_client)
        self.metadata_db = MetadataDB()

    def run(
        self,
        pipeline_run_id: str,
        cluster_label_run_id: str | None = None,
        segments_run_id: str | None = None,
        *,
        skip_validation: bool = False,
        validation_run_id: str | None = None,
    ) -> SynthesizeValidateResult:
        cluster_run = cluster_label_run_id or pipeline_run_id
        seg_run = segments_run_id or cluster_run

        proc_dir = resolve_path(self.settings.paths.processed_data)
        analyses_path = proc_dir / f"analyses_{cluster_run}.json"
        clusters_path = proc_dir / f"clusters_{cluster_run}.json"
        search_gap_path = proc_dir / f"search_gap_{cluster_run}.json"

        if not analyses_path.exists():
            raise FileNotFoundError(f"Missing {analyses_path}. Run cluster_label first.")
        if not clusters_path.exists():
            raise FileNotFoundError(
                f"Missing {clusters_path}. Re-run cluster_label to persist cluster memberships."
            )

        analyses = load_analyses(analyses_path)
        cluster_members = load_cluster_memberships(clusters_path)
        segments = load_segments(resolve_segments_path(seg_run, self.settings))
        search_gaps = (
            load_search_gap_themes(search_gap_path) if search_gap_path.exists() else []
        )

        result = SynthesizeValidateResult(
            pipeline_run_id=pipeline_run_id,
            cluster_label_run_id=cluster_run,
            segments_run_id=seg_run,
        )

        self.metadata_db.start_pipeline_stage(pipeline_run_id, "synthesize_validate")
        log_event(
            logger,
            logging.INFO,
            "synthesize_validate started",
            run_id=pipeline_run_id,
            stage="synthesize_validate",
            counts={"analyses": len(analyses), "search_gap_themes": len(search_gaps)},
        )

        agreement_by_cluster: dict[str, float] | None = None

        try:
            if not skip_validation and analyses:
                val_id = validation_run_id or f"val_{pipeline_run_id}"
                val_result = self.validation_mod.run(
                    validation_run_id=val_id,
                    pipeline_run_id=pipeline_run_id,
                    analyses=analyses,
                    clusters_path=clusters_path,
                    segments_run_id=seg_run,
                )
                result.validation = val_result.summary()
                result.validation_path = str(
                    self.validation_mod.write_validation_artifact(
                        val_result, pipeline_run_id
                    )
                )
                agreement_by_cluster = val_result.agreement_by_cluster
                self.metadata_db.save_validation_run(val_result.validation_run)

            synth_result = self.synthesis_mod.run(
                analyses,
                cluster_members,
                segments,
                search_gaps,
                agreement_by_cluster=agreement_by_cluster,
            )

            insights_dir = resolve_path(self.settings.paths.insights)
            insights_dir.mkdir(parents=True, exist_ok=True)
            insights_path = insights_dir / f"insights_{pipeline_run_id}.json"
            insights_path.write_text(
                json.dumps(
                    [c.model_dump(mode="json") for c in synth_result.insight_cards],
                    indent=2,
                ),
                encoding="utf-8",
            )

            result.insight_cards = synth_result.insight_cards
            result.insights_path = str(insights_path)
            result.synthesis = synth_result.summary()

            for card in synth_result.insight_cards:
                self.metadata_db.save_insight(
                    pipeline_run_id,
                    card,
                    cluster_label_run_id=cluster_run,
                )

            summary_path = proc_dir / f"synthesize_validate_summary_{pipeline_run_id}.json"
            summary_path.write_text(
                json.dumps(result.to_dict(), indent=2),
                encoding="utf-8",
            )

            self.metadata_db.finish_pipeline_stage(
                pipeline_run_id,
                "synthesize_validate",
                status="completed",
                counts=result.to_dict(),
            )
        except Exception:
            self.metadata_db.finish_pipeline_stage(
                pipeline_run_id,
                "synthesize_validate",
                status="failed",
            )
            raise

        return result
