"""Staleness flag when evidence is older than 12 months."""

from datetime import datetime, timedelta, timezone

from models.clusters import SearchGapTheme
from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
from models.records import CleanSegment, SentenceSegment
from pipeline.synthesize import SynthesisModule


def test_stale_insight_flagged() -> None:
    old = datetime.now(timezone.utc) - timedelta(days=400)
    base = SentenceSegment(
        segment_id="s1",
        record_id="r1",
        text="Wish they had more brands",
        sentence_index=0,
        platform="play_store",
        rating=4,
        created_at=old,
        url="https://example.com",
    )
    seg = CleanSegment(**base.model_dump(), normalized_text=base.text, embed_text=base.text)
    analysis = ClusterAnalysis(
        cluster_id="c1",
        friction=CrossShoppingFrictionAnalysis(
            user_cognitive_barrier="ASSORTMENT_GAP",
            funnel_leak_stage="CONSIDERATION",
            price_sensitivity_detected=False,
        ),
        theme_label="Missing brands",
        related_RQs=["RQ8"],
    )
    theme = SearchGapTheme(
        cluster_id="sg1",
        theme_label="missing brands",
        top_terms=["missing", "brands"],
        segment_ids=["s1"],
        segment_count=1,
    )
    mod = SynthesisModule()
    cards = mod.run([analysis], {"c1": ["s1"]}, [seg], [theme]).insight_cards
    assert any(c.is_stale for c in cards)
