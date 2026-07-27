"""Assert exactly one Groq API call per discovery cluster."""

import numpy as np

from pipeline.cluster import DiscoveryCluster
from pipeline.groq_labeler import GroqLabeler, MockGroqClient


def _make_cluster(cluster_id: str, n_segments: int) -> DiscoveryCluster:
    prefix = cluster_id.replace("disc_", "")
    return DiscoveryCluster(
        cluster_id=cluster_id,
        segment_ids=[f"s{prefix}_{i}" for i in range(n_segments)],
        centroid=np.ones(384, dtype=np.float32) / np.sqrt(384),
    )


def test_exactly_one_api_call_per_cluster(tmp_path) -> None:
    MockGroqClient.call_count = 0
    client = MockGroqClient()
    from pipeline.groq_labeler import LabelCache

    labeler = GroqLabeler(client=client, cache=LabelCache(path=tmp_path / "label_cache.json"))

    clusters = [_make_cluster(f"disc_{i:04d}", 5) for i in range(5)]
    result = labeler.label_clusters(clusters)

    assert MockGroqClient.call_count == 5
    assert result.api_call_count == 5
    assert len(result.analyses) == 5
    assert result.cache_hits == 0


def test_cache_prevents_duplicate_api_calls(tmp_path) -> None:
    MockGroqClient.call_count = 0
    client = MockGroqClient()
    from pipeline.groq_labeler import LabelCache

    labeler = GroqLabeler(client=client, cache=LabelCache(path=tmp_path / "label_cache.json"))

    cluster = _make_cluster("disc_0000", 3)
    cluster.compute_hash("1.0.0")

    labeler.label_cluster(cluster)
    labeler.label_cluster(cluster)

    assert MockGroqClient.call_count == 1

    result = labeler.label_clusters([cluster])
    assert result.cache_hits >= 1
