"""Conflict policy — opposing barriers produce separate insight cards."""

from datetime import datetime, timezone

from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
from models.records import CleanSegment, SentenceSegment
from pipeline.synthesize import SynthesisModule


def _make(cluster_id: str, barrier: str) -> ClusterAnalysis:
    return ClusterAnalysis(
        cluster_id=cluster_id,
        friction=CrossShoppingFrictionAnalysis(
            user_cognitive_barrier=barrier,  # type: ignore[arg-type]
            funnel_leak_stage="CONSIDERATION",
            price_sensitivity_detected=False,
        ),
        theme_label="Electronics trust issues",
        related_RQs=["RQ5"],
    )


def _seg(sid: str) -> CleanSegment:
    base = SentenceSegment(
        segment_id=sid,
        record_id=f"r_{sid}",
        text="Worried about fake electronics on Blinkit",
        sentence_index=0,
        platform="play_store",
        rating=3,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://example.com",
    )
    return CleanSegment(**base.model_dump(), normalized_text=base.text, embed_text=base.text)


def test_opposing_barriers_separate_cards() -> None:
    mod = SynthesisModule()
    analyses = [
        _make("c1", "AUTHENTICITY_DISTRUST"),
        _make("c2", "RETURN_POLICY_ANXIETY"),
    ]
    members = {"c1": ["s1"], "c2": ["s2"]}
    segments = [_seg("s1"), _seg("s2")]
    cards = mod.run(analyses, members, segments, []).insight_cards
    assert len(cards) == 2
    assert cards[0].insight_id != cards[1].insight_id
