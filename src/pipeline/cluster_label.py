"""Orchestrator for Phase 3 — dual-track cluster + Groq label."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from common.config import AppSettings, load_settings, resolve_path
from common.logging import get_logger, log_event
from models.clusters import SearchGapTheme
from models.friction import ClusterAnalysis
from models.records import CleanSegment
from pipeline.cluster import ClusterModule, ClusterResult
from pipeline.groq_labeler import GroqClient, GroqLabeler, LabelResult
from pipeline.search_gap import SearchGapModule, SearchGapResult
from storage.embedding_cache import EmbeddingCache
from storage.metadata_db import MetadataDB
from storage.vector_store import VectorStore

logger = get_logger(__name__)


@dataclass
class ClusterLabelResult:
    pipeline_run_id: str
    segments_run_id: str
    discovery: dict = field(default_factory=dict)
    search_gap: dict = field(default_factory=dict)
    groq: dict = field(default_factory=dict)
    analyses_path: str | None = None
    search_gap_path: str | None = None
    groq_audit_path: str | None = None
    cluster_analyses: list[ClusterAnalysis] = field(default_factory=list)
    search_gap_themes: list[SearchGapTheme] = field(default_factory=list)
    total_segments: int = 0

    def to_dict(self) -> dict:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "segments_run_id": self.segments_run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_segments": self.total_segments,
            "discovery": self.discovery,
            "search_gap": self.search_gap,
            "groq": self.groq,
            "analyses_path": self.analyses_path,
            "search_gap_path": self.search_gap_path,
            "groq_audit_path": self.groq_audit_path,
        }


def load_segments(segments_path: Path) -> list[CleanSegment]:
    segments: list[CleanSegment] = []
    with segments_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                segments.append(CleanSegment.model_validate_json(line))
    return segments


def resolve_segments_path(
    segments_run_id: str,
    settings: AppSettings,
) -> Path:
    segments_dir = resolve_path(f"{settings.paths.processed_data}/segments")
    path = segments_dir / f"segments_{segments_run_id}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Segments file not found: {path}. Run clean_embed first."
        )
    return path


def load_embeddings_for_segments(
    segments: list[CleanSegment],
    *,
    vector_store: VectorStore | None = None,
    cache: EmbeddingCache | None = None,
    model_version: str,
) -> np.ndarray:
    """Load embeddings from vector store, falling back to embedding cache."""
    store = vector_store or VectorStore()
    emb_cache = cache or EmbeddingCache()

    segment_ids = [s.segment_id for s in segments]
    stored = store.get_by_ids(segment_ids)

    id_to_embedding: dict[str, np.ndarray] = {}
    if stored.get("ids"):
        for sid, emb in zip(stored["ids"], stored["embeddings"], strict=True):
            if emb is not None:
                id_to_embedding[sid] = np.asarray(emb, dtype=np.float32)

    missing_segments: list[CleanSegment] = []
    for seg in segments:
        if seg.segment_id not in id_to_embedding and seg.embed_text.strip():
            missing_segments.append(seg)

    if missing_segments:
        texts = [s.embed_text for s in missing_segments]
        cached = emb_cache.get_many(texts, model_version)
        for seg, text in zip(missing_segments, texts, strict=True):
            vec = cached.get(text)
            if vec is not None:
                id_to_embedding[seg.segment_id] = np.asarray(vec, dtype=np.float32)

    vectors: list[np.ndarray] = []
    for seg in segments:
        vec = id_to_embedding.get(seg.segment_id)
        if vec is None:
            raise ValueError(
                f"No embedding for segment {seg.segment_id}. Run clean_embed first."
            )
        vectors.append(vec)

    return np.stack(vectors, axis=0)


class ClusterLabelPipeline:
    """Run Track A + Track B in parallel, then Groq label discovery clusters."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        vector_store: VectorStore | None = None,
        cache: EmbeddingCache | None = None,
        groq_client=None,
    ) -> None:
        self.settings = settings or load_settings()
        self.cluster_mod = ClusterModule(self.settings)
        self.search_gap_mod = SearchGapModule(self.settings)
        self.vector_store = vector_store or VectorStore()
        self.cache = cache or EmbeddingCache()
        self.groq_client = groq_client
        self.metadata_db = MetadataDB()

    def run(
        self,
        pipeline_run_id: str,
        segments_run_id: str | None = None,
        *,
        skip_groq: bool = False,
    ) -> ClusterLabelResult:
        effective_segments_run = segments_run_id or pipeline_run_id
        segments_path = resolve_segments_path(effective_segments_run, self.settings)
        segments = load_segments(segments_path)

        result = ClusterLabelResult(
            pipeline_run_id=pipeline_run_id,
            segments_run_id=effective_segments_run,
            total_segments=len(segments),
        )

        self.metadata_db.start_pipeline_stage(pipeline_run_id, "cluster_label")
        log_event(
            logger,
            logging.INFO,
            "cluster_label started",
            run_id=pipeline_run_id,
            stage="cluster_label",
            counts={"segments": len(segments)},
        )

        try:
            embeddings = load_embeddings_for_segments(
                segments,
                vector_store=self.vector_store,
                cache=self.cache,
                model_version=self.settings.embedding.model,
            )

            discovery_result: ClusterResult | None = None
            search_gap_result: SearchGapResult | None = None

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_discovery = executor.submit(
                    self.cluster_mod.run_discovery, segments, embeddings
                )
                future_search_gap = executor.submit(
                    self.search_gap_mod.run, segments, embeddings
                )
                for future in as_completed([future_discovery, future_search_gap]):
                    if future is future_discovery:
                        discovery_result = future.result()
                    else:
                        search_gap_result = future.result()

            assert discovery_result is not None
            assert search_gap_result is not None

            result.discovery = discovery_result.summary()
            result.search_gap = search_gap_result.summary()
            result.search_gap_themes = search_gap_result.themes

            log_event(
                logger,
                logging.INFO,
                "dual-track clustering complete",
                run_id=pipeline_run_id,
                stage="cluster",
                counts={
                    "discovery_clusters": result.discovery.get("cluster_count", 0),
                    "search_gap_themes": result.search_gap.get("theme_count", 0),
                },
            )

            if not skip_groq:
                client = self.groq_client
                if client is None:
                    client = GroqClient(self.settings)
                labeler = GroqLabeler(self.settings, client=client)
                label_result: LabelResult = labeler.label_clusters(
                    discovery_result.clusters,
                    run_id=pipeline_run_id,
                )
                result.cluster_analyses = label_result.analyses
                result.groq = label_result.summary()
                result.groq_audit_path = str(
                    self._write_groq_audit(label_result, pipeline_run_id)
                )
            else:
                result.groq = {"skipped": True}

            proc_dir = resolve_path(self.settings.paths.processed_data)
            analyses_path = proc_dir / f"analyses_{pipeline_run_id}.json"
            analyses_path.write_text(
                json.dumps(
                    [a.model_dump(mode="json") for a in result.cluster_analyses],
                    indent=2,
                ),
                encoding="utf-8",
            )
            result.analyses_path = str(analyses_path)

            sg_path = proc_dir / f"search_gap_{pipeline_run_id}.json"
            sg_path.write_text(
                json.dumps(
                    [t.model_dump(mode="json") for t in result.search_gap_themes],
                    indent=2,
                ),
                encoding="utf-8",
            )
            result.search_gap_path = str(sg_path)

            summary_path = proc_dir / f"cluster_label_summary_{pipeline_run_id}.json"
            summary_path.write_text(
                json.dumps(result.to_dict(), indent=2),
                encoding="utf-8",
            )

            self.metadata_db.finish_pipeline_stage(
                pipeline_run_id,
                "cluster_label",
                status="completed",
                counts=result.to_dict(),
            )
        except Exception:
            self.metadata_db.finish_pipeline_stage(
                pipeline_run_id,
                "cluster_label",
                status="failed",
            )
            raise

        return result

    def _write_groq_audit(self, label_result: LabelResult, run_id: str) -> Path:
        proc_dir = resolve_path(self.settings.paths.processed_data)
        audit = {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": label_result.summary(),
            "calls": [
                {
                    "cluster_id": r.cluster_id,
                    "cluster_hash": r.cluster_hash,
                    "tokens_used": r.tokens_used,
                    "status": r.status,
                    "from_cache": r.from_cache,
                }
                for r in label_result.call_records
            ],
        }
        path = proc_dir / f"groq_audit_{run_id}.json"
        path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        return path
