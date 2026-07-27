"""Every insight card maps to at least one RQ."""

from datetime import datetime, timezone

from models.insights import InsightCard


def test_insight_card_requires_rq() -> None:
    card = InsightCard(
        insight_id="abc123",
        statement="Test insight",
        related_RQs=["RQ1", "RQ3"],
        evidence_count=10,
        source_diversity=2,
        cognitive_barrier_split={"AWARENESS_DEFICIT": 1.0},
        dominant_funnel_leak_stage="DISCOVERY",
        confidence_tier="high",
        created_at=datetime.now(timezone.utc),
    )
    assert len(card.related_RQs) >= 1


def test_synthesis_cards_have_rq(tmp_path, monkeypatch) -> None:
    from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
    from models.records import CleanSegment, SentenceSegment
    from pipeline.synthesize import SynthesisModule

    analysis = ClusterAnalysis(
        cluster_id="c1",
        friction=CrossShoppingFrictionAnalysis(
            user_cognitive_barrier="AWARENESS_DEFICIT",
            funnel_leak_stage="DISCOVERY",
            price_sensitivity_detected=False,
        ),
        theme_label="Unaware of categories",
        related_RQs=["RQ2", "RQ3"],
    )
    base = SentenceSegment(
        segment_id="s1",
        record_id="r1",
        text="Never tried baby care on Blinkit",
        sentence_index=0,
        platform="reddit",
        rating=4,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://example.com",
    )
    seg = CleanSegment(**base.model_dump(), normalized_text=base.text, embed_text=base.text)
    cards = SynthesisModule().run([analysis], {"c1": ["s1"]}, [seg], []).insight_cards
    assert all(len(c.related_RQs) >= 1 for c in cards)
