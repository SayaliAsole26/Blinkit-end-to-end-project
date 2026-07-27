"""Tests for discovery clustering — HDBSCAN, dedup merge, representatives."""

from datetime import datetime, timezone

import numpy as np
import pytest

from models.records import CleanSegment, SentenceSegment
from pipeline.cluster import (
    ClusterModule,
    DiscoveryCluster,
    cosine_similarity,
    merge_similar_clusters,
    select_representatives,
)


def _segment(
    text: str,
    segment_id: str,
    *,
    platform: str = "play_store",
    categories: list[str] | None = None,
    logistics: bool = False,
) -> CleanSegment:
    base = SentenceSegment(
        segment_id=segment_id,
        record_id=f"rec_{segment_id}",
        text=text,
        sentence_index=0,
        platform=platform,  # type: ignore[arg-type]
        rating=4,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url=f"https://example.com/{segment_id}",
    )
    return CleanSegment(
        **base.model_dump(),
        normalized_text=text,
        embed_text=text,
        category_mentions=categories or [],
        is_logistics_only=logistics,
    )


def _unit_vector(seed: int, dim: int = 384) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def test_cosine_similarity_identical() -> None:
    v = _unit_vector(42)
    assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-5)


def test_merge_similar_clusters() -> None:
    v1 = _unit_vector(1)
    v2 = v1 * 0.99 + _unit_vector(2) * 0.01
    v2 /= np.linalg.norm(v2)
    v3 = _unit_vector(99)

    c1 = DiscoveryCluster(cluster_id="c1", segment_ids=["s1", "s2"], centroid=v1)
    c2 = DiscoveryCluster(cluster_id="c2", segment_ids=["s3"], centroid=v2)
    c3 = DiscoveryCluster(cluster_id="c3", segment_ids=["s4"], centroid=v3)

    merged = merge_similar_clusters([c1, c2, c3], threshold=0.90)
    assert len(merged) == 2
    merged_sizes = sorted(len(c.segment_ids) for c in merged)
    assert merged_sizes == [1, 3]


def test_select_representatives_diversity() -> None:
    segments = [
        _segment("pet food missing", "s1", platform="play_store", categories=["pet_supplies"]),
        _segment("pet food gap", "s2", platform="reddit", categories=["pet_supplies"]),
        _segment("baby diapers", "s3", platform="app_store", categories=["baby_care"]),
    ]
    vectors = np.stack([_unit_vector(i) for i in range(3)])
    reps = select_representatives(segments, vectors, min_count=2, max_count=3)
    assert 2 <= len(reps) <= 3
    platforms = {r.platform for r in reps}
    assert len(platforms) >= 2


def test_cluster_module_excludes_logistics() -> None:
    segments = [
        _segment("Never tried electronics here", "s1", categories=["electronics"]),
        _segment("Great groceries", "s2", categories=["groceries"]),
        _segment("Also no baby care", "s3", categories=["baby_care"]),
        _segment("Delivery was late again", "s4", logistics=True),
    ]
    base = _unit_vector(10)
    vectors = np.stack([
        base + _unit_vector(i) * 0.05 for i in range(len(segments))
    ])
    for i, row in enumerate(vectors):
        vectors[i] = row / np.linalg.norm(row)

    mod = ClusterModule()
    result = mod.run_discovery(segments, vectors)
    assert result.input_count == 3
    assert result.summary()["cluster_count"] >= 1
    all_ids = {sid for c in result.clusters for sid in c.segment_ids}
    assert "s4" not in all_ids
