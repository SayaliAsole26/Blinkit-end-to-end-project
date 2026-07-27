"""Every cluster analysis must map to at least one RQ."""

import numpy as np

from pipeline.cluster import DiscoveryCluster
from pipeline.groq_labeler import GroqLabeler, MockGroqClient


def test_every_analysis_has_rq_tags() -> None:
    MockGroqClient.call_count = 0
    labeler = GroqLabeler(client=MockGroqClient())

    clusters = [
        DiscoveryCluster(
            cluster_id=f"disc_{i:04d}",
            segment_ids=[f"s{i}a", f"s{i}b"],
            centroid=np.ones(384) / np.sqrt(384),
        )
        for i in range(3)
    ]
    result = labeler.label_clusters(clusters)

    assert len(result.analyses) == 3
    for analysis in result.analyses:
        assert len(analysis.related_RQs) >= 1
        for rq in analysis.related_RQs:
            assert rq.startswith("RQ")


def test_unlabeled_fallback_has_rq() -> None:
    from pipeline.groq_labeler import _default_unlabeled

    analysis = _default_unlabeled("disc_fail", "1.0.0")
    assert len(analysis.related_RQs) >= 1
