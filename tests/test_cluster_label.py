"""Integration test for cluster_label pipeline (Phase 3)."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from common.config import load_settings
from models.records import CleanSegment, SentenceSegment
from pipeline.cluster_label import ClusterLabelPipeline
from pipeline.embed import MockEmbedder
from storage.embedding_cache import EmbeddingCache
from storage.vector_store import VectorStore
from pipeline.groq_labeler import MockGroqClient


def _clean(text: str, sid: str, *, logistics: bool = False) -> CleanSegment:
    base = SentenceSegment(
        segment_id=sid,
        record_id=f"rec_{sid}",
        text=text,
        sentence_index=0,
        platform="play_store",
        rating=4,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url=f"https://example.com/{sid}",
    )
    return CleanSegment(
        **base.model_dump(),
        normalized_text=text,
        embed_text=text,
        category_mentions=["electronics"],
        is_logistics_only=logistics,
    )


def test_cluster_label_e2e(tmp_path: Path, monkeypatch) -> None:
    settings = load_settings()
    proc_dir = tmp_path / "processed"
    segments_dir = proc_dir / "segments"
    segments_dir.mkdir(parents=True)
    cache_path = tmp_path / "emb.db"
    chroma_path = tmp_path / "chroma"

    def _resolve(rel: str) -> Path:
        if rel.startswith("data/processed"):
            suffix = rel.removeprefix("data/processed/").removeprefix("data/processed")
            if suffix:
                target = proc_dir / suffix
                target.parent.mkdir(parents=True, exist_ok=True)
                return target
            return proc_dir
        if "metadata" in rel:
            return tmp_path / "metadata.db"
        return tmp_path / Path(rel).name

    for mod in (
        "common.config",
        "pipeline.cluster_label",
        "pipeline.groq_labeler",
        "storage.metadata_db",
    ):
        monkeypatch.setattr(f"{mod}.resolve_path", _resolve)

    segments = [
        _clean("Never tried electronics on Blinkit, always use Amazon", f"s{i}")
        for i in range(8)
    ] + [
        _clean("Couldn't find dog food brands I wanted", f"sg{i}")
        for i in range(8)
    ] + [
        _clean("Delivery was very late", "log1", logistics=True),
    ]

    segments_path = segments_dir / "segments_pipeline_p3.jsonl"
    with segments_path.open("w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg.model_dump_json())
            f.write("\n")

    embedder = MockEmbedder(dimensions=384)
    texts = [s.embed_text for s in segments if not s.embed_skipped]
    vectors = embedder.encode(texts, batch_size=64)

    store = VectorStore(persist_dir=chroma_path)
    ids = [s.segment_id for s in segments if not s.embed_skipped]
    store.upsert_segments(
        ids,
        vectors.tolist(),
        texts,
        [{"platform": s.platform, "is_logistics_only": s.is_logistics_only} for s in segments if not s.embed_skipped],
    )

    MockGroqClient.call_count = 0
    pipeline = ClusterLabelPipeline(
        settings=settings,
        vector_store=store,
        cache=EmbeddingCache(db_path=cache_path),
        groq_client=MockGroqClient(),
    )

    result = pipeline.run("pipeline_p3", segments_run_id="pipeline_p3")
    assert result.total_segments == len(segments)
    assert result.discovery.get("cluster_count", 0) >= 1
    assert result.search_gap.get("theme_count", 0) >= 0
    assert len(result.cluster_analyses) >= 1
    assert all(len(a.related_RQs) >= 1 for a in result.cluster_analyses)
    assert Path(result.analyses_path).exists()
    assert Path(result.search_gap_path).exists()
    assert MockGroqClient.call_count == result.discovery.get("cluster_count", 0)
