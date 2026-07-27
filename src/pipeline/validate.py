"""Stage 11 — Validation: inter-run Groq agreement + human audit support."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from common.config import AppSettings, load_settings, resolve_path
from common.logging import get_logger
from models.friction import ClusterAnalysis
from models.validation import ValidationRun
from pipeline.cluster import DiscoveryCluster
from pipeline.groq_labeler import GroqClient, GroqLabeler

logger = get_logger(__name__)


@dataclass
class AgreementDetail:
    cluster_id: str
    barrier_match: bool
    funnel_match: bool
    competitor_match: bool
    overall_match: bool


@dataclass
class ValidationResult:
    validation_run: ValidationRun
    details: list[AgreementDetail] = field(default_factory=list)
    agreement_by_cluster: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "agreement_rate": self.validation_run.agreement_rate,
            "barrier_agreement": self.validation_run.barrier_agreement,
            "funnel_agreement": self.validation_run.funnel_agreement,
            "competitor_agreement": self.validation_run.competitor_agreement,
            "sample_size": self.validation_run.sample_size,
        }


def field_agreement(original: ClusterAnalysis, resample: ClusterAnalysis) -> AgreementDetail:
    barrier_match = (
        original.friction.user_cognitive_barrier
        == resample.friction.user_cognitive_barrier
    )
    funnel_match = (
        original.friction.funnel_leak_stage == resample.friction.funnel_leak_stage
    )
    competitor_match = (
        original.friction.competitor_entity == resample.friction.competitor_entity
        and original.friction.competitor_advantage == resample.friction.competitor_advantage
    )
    overall = barrier_match and funnel_match
    return AgreementDetail(
        cluster_id=original.cluster_id,
        barrier_match=barrier_match,
        funnel_match=funnel_match,
        competitor_match=competitor_match,
        overall_match=overall,
    )


def simple_kappa(matches: list[bool]) -> float | None:
    if not matches:
        return None
    p_o = sum(matches) / len(matches)
    return round(2 * p_o - 1, 4)


def rebuild_discovery_cluster(
    entry: dict,
    segments_run_id: str,
    settings: AppSettings,
) -> DiscoveryCluster:
    import numpy as np

    from pipeline.cluster_label import load_segments, resolve_segments_path

    segments = load_segments(resolve_segments_path(segments_run_id, settings))
    seg_by_id = {s.segment_id: s for s in segments}
    reps = [seg_by_id[sid] for sid in entry["segment_ids"][:10] if sid in seg_by_id]
    return DiscoveryCluster(
        cluster_id=entry["cluster_id"],
        segment_ids=entry["segment_ids"],
        centroid=np.zeros(384, dtype=np.float32),
        representatives=reps,
        category_distribution=entry.get("category_distribution", {}),
        platform_distribution=entry.get("platform_distribution", {}),
        competitor_mentions=entry.get("competitor_mentions", []),
        cluster_hash=entry.get("cluster_hash", ""),
    )


class ValidationModule:
    """10% cluster re-sample via Groq; compute agreement metrics."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        groq_client=None,
    ) -> None:
        self.settings = settings or load_settings()
        self.groq_client = groq_client

    def run(
        self,
        validation_run_id: str,
        pipeline_run_id: str,
        analyses: list[ClusterAnalysis],
        clusters_path: Path,
        segments_run_id: str,
        *,
        seed: int = 42,
    ) -> ValidationResult:
        cluster_data = json.loads(clusters_path.read_text(encoding="utf-8"))
        analysis_by_id = {a.cluster_id: a for a in analyses}
        eligible_ids = [c["cluster_id"] for c in cluster_data if c["cluster_id"] in analysis_by_id]

        rate = self.settings.validation.resample_rate
        sample_size = max(1, int(len(eligible_ids) * rate)) if eligible_ids else 0
        rng = random.Random(seed)
        sampled_ids = rng.sample(eligible_ids, min(sample_size, len(eligible_ids)))

        cluster_by_id = {c["cluster_id"]: c for c in cluster_data}
        labeler = GroqLabeler(
            self.settings,
            client=self.groq_client or GroqClient(self.settings),
        )

        details: list[AgreementDetail] = []
        for cid in sampled_ids:
            original = analysis_by_id[cid]
            cluster = rebuild_discovery_cluster(
                cluster_by_id[cid], segments_run_id, self.settings
            )
            try:
                resample, _ = labeler.label_cluster(cluster, skip_cache=True)
                details.append(field_agreement(original, resample))
            except Exception as exc:
                logger.warning("Validation resample failed for %s: %s", cid, exc)

        barrier_rate = (
            sum(d.barrier_match for d in details) / len(details) if details else 0.0
        )
        funnel_rate = (
            sum(d.funnel_match for d in details) / len(details) if details else 0.0
        )
        competitor_rate = (
            sum(d.competitor_match for d in details) / len(details) if details else 0.0
        )
        overall_rate = (
            sum(d.overall_match for d in details) / len(details) if details else 0.0
        )

        agreement_by_cluster = {
            d.cluster_id: 1.0 if d.overall_match else 0.0 for d in details
        }

        validation_run = ValidationRun(
            run_id=validation_run_id,
            pipeline_run_id=pipeline_run_id,
            sample_size=len(details),
            agreement_rate=round(overall_rate, 4),
            barrier_agreement=round(barrier_rate, 4),
            funnel_agreement=round(funnel_rate, 4),
            competitor_agreement=round(competitor_rate, 4),
            cohens_kappa_barrier=simple_kappa([d.barrier_match for d in details]),
            created_at=datetime.now(timezone.utc),
            taxonomy_version=self.settings.taxonomy_version,
        )

        return ValidationResult(
            validation_run=validation_run,
            details=details,
            agreement_by_cluster=agreement_by_cluster,
        )

    def write_validation_artifact(
        self,
        result: ValidationResult,
        pipeline_run_id: str,
    ) -> Path:
        proc_dir = resolve_path(self.settings.paths.processed_data)
        path = proc_dir / f"validation_{pipeline_run_id}.json"
        payload = {
            "validation_run": result.validation_run.model_dump(mode="json"),
            "details": [d.__dict__ for d in result.details],
            "summary": result.summary(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
