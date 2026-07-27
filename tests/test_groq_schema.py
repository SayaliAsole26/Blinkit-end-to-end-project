"""Tests for Groq labeler schema validation."""

import json

from pipeline.cluster import DiscoveryCluster
from pipeline.groq_labeler import GroqLabeler, MockGroqClient, build_cluster_prompt
from models.friction import ClusterAnalysis


def test_mock_groq_returns_valid_cluster_analysis(tmp_path) -> None:
    MockGroqClient.call_count = 0
    client = MockGroqClient()
    from pipeline.groq_labeler import LabelCache

    cluster = DiscoveryCluster(
        cluster_id="disc_0001",
        segment_ids=["s1", "s2", "s3"],
        centroid=__import__("numpy").zeros(384),
    )
    labeler = GroqLabeler(client=client, cache=LabelCache(path=tmp_path / "cache.json"))
    analysis, record = labeler.label_cluster(cluster)

    assert isinstance(analysis, ClusterAnalysis)
    assert analysis.cluster_id == "disc_0001"
    assert analysis.friction.user_cognitive_barrier
    assert analysis.theme_label
    assert len(analysis.related_RQs) >= 1
    assert record.status == "success"
    assert record.tokens_used == 100


def test_build_cluster_prompt_includes_context() -> None:
    cluster = DiscoveryCluster(
        cluster_id="disc_0002",
        segment_ids=["s1"],
        centroid=__import__("numpy").zeros(384),
        category_distribution={"pet_supplies": 2},
        platform_distribution={"play_store": 2},
        competitor_mentions=["Amazon"],
    )
    prompt = build_cluster_prompt(cluster, "1.0.0")
    assert "pet_supplies" in prompt
    assert "Amazon" in prompt
    assert "disc_0002" in prompt


def test_groq_json_parses_to_cluster_analysis() -> None:
    payload = {
        "cluster_id": "disc_test",
        "friction": {
            "user_cognitive_barrier": "RETURN_POLICY_ANXIETY",
            "funnel_leak_stage": "CONSIDERATION",
            "competitor_entity": "Amazon",
            "competitor_advantage": "RETURN_POLICY",
            "price_sensitivity_detected": False,
        },
        "theme_label": "Return policy concerns for electronics",
        "related_RQs": ["RQ5", "RQ6"],
        "segment_relevance": ["electronics_buyers"],
        "taxonomy_version": "1.0.0",
    }
    raw = json.dumps(payload)
    analysis = GroqLabeler(client=MockGroqClient())._parse_response(raw, "disc_test")
    assert analysis.friction.user_cognitive_barrier == "RETURN_POLICY_ANXIETY"
    assert "RQ5" in analysis.related_RQs
