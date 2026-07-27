"""Synthesis module tests — ranking, barrier split, confidence rules."""

from collections import Counter
from datetime import datetime, timezone

import pytest

from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
from models.records import CleanSegment, SentenceSegment
from pipeline.synthesize import (
    SynthesisModule,
    _barrier_split,
    assign_confidence_tier,
    paraphrase_snippet,
)


def _analysis(cluster_id: str, theme: str, barrier: str) -> ClusterAnalysis:
    return ClusterAnalysis(
        cluster_id=cluster_id,
        friction=CrossShoppingFrictionAnalysis(
            user_cognitive_barrier=barrier,  # type: ignore[arg-type]
            funnel_leak_stage="DISCOVERY",
            competitor_entity=None,
            competitor_advantage=None,
            price_sensitivity_detected=False,
        ),
        theme_label=theme,
        related_RQs=["RQ2"],
    )


def _segment(sid: str, text: str, platform: str = "play_store") -> CleanSegment:
    base = SentenceSegment(
        segment_id=sid,
        record_id=f"rec_{sid}",
        text=text,
        sentence_index=0,
        platform=platform,  # type: ignore[arg-type]
        rating=4,
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        url=f"https://example.com/{sid}",
    )
    return CleanSegment(
        **base.model_dump(),
        normalized_text=text,
        embed_text=text,
    )


def test_barrier_split_sums_to_one() -> None:
    split = _barrier_split(Counter({"AWARENESS_DEFICIT": 2, "ASSORTMENT_GAP": 2}))
    assert pytest.approx(sum(split.values()), abs=1e-6) == 1.0


def test_confidence_tier_high_requires_two_platforms() -> None:
    assert assign_confidence_tier(2) == "high"
    assert assign_confidence_tier(1) == "medium"


def test_paraphrase_differs_from_verbatim() -> None:
    raw = "Blinkit never has pet food brands I want."
    para = paraphrase_snippet(raw)
    assert para.lower() != raw.lower()


def test_synthesis_conflict_policy_separate_cards() -> None:
    mod = SynthesisModule()
    analyses = [
        _analysis("c1", "Pet supplies gap", "ASSORTMENT_GAP"),
        _analysis("c2", "Pet supplies gap", "AWARENESS_DEFICIT"),
    ]
    members = {"c1": ["s1"], "c2": ["s2"]}
    segments = [
        _segment("s1", "Couldn't find dog food on Blinkit"),
        _segment("s2", "Didn't know Blinkit sells pet food", "reddit"),
    ]
    result = mod.run(analyses, members, segments, [])
    assert len(result.insight_cards) == 2
    barrier_keys = [
        next(iter(c.cognitive_barrier_split.keys())) for c in result.insight_cards
    ]
    assert len(set(barrier_keys)) == 2
