"""Schema validation tests for UnifiedRecord and related models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
from models.insights import InsightCard
from models.records import UnifiedRecord, compute_record_id


def test_unified_record_valid() -> None:
    record = UnifiedRecord.build(
        platform="play_store",
        raw_text="  Great app with trailing space  ",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://play.google.com/review/1",
        ingestion_run_id="ingest_test",
        rating=5,
    )
    assert record.platform == "play_store"
    assert record.raw_text == "  Great app with trailing space  "
    assert record.rating == 5


def test_unified_record_invalid_platform() -> None:
    with pytest.raises(ValidationError):
        UnifiedRecord.build(
            platform="invalid",  # type: ignore[arg-type]
            raw_text="text",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            url="https://example.com",
            ingestion_run_id="run",
        )


def test_unified_record_invalid_rating() -> None:
    with pytest.raises(ValidationError):
        UnifiedRecord.build(
            platform="reddit",
            raw_text="text",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            url="https://reddit.com/x",
            ingestion_run_id="run",
            rating=6,
        )


def test_reddit_null_rating_allowed() -> None:
    record = UnifiedRecord.build(
        platform="reddit",
        raw_text="Where is pet food on Blinkit?",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://reddit.com/r/india/1",
        ingestion_run_id="run",
        rating=None,
    )
    assert record.rating is None


def test_friction_analysis_invalid_barrier() -> None:
    with pytest.raises(ValidationError):
        CrossShoppingFrictionAnalysis(
            user_cognitive_barrier="NEGATIVE",  # type: ignore[arg-type]
            funnel_leak_stage="DISCOVERY",
            price_sensitivity_detected=False,
        )


def test_friction_analysis_valid() -> None:
    analysis = CrossShoppingFrictionAnalysis(
        user_cognitive_barrier="ASSORTMENT_GAP",
        funnel_leak_stage="CONSIDERATION",
        competitor_entity="Amazon",
        competitor_advantage="ASSORTMENT",
        price_sensitivity_detected=True,
    )
    assert analysis.competitor_entity == "Amazon"


def test_cluster_analysis_requires_rq() -> None:
    with pytest.raises(ValidationError):
        ClusterAnalysis(
            cluster_id="c1",
            friction=CrossShoppingFrictionAnalysis(
                user_cognitive_barrier="AWARENESS_DEFICIT",
                funnel_leak_stage="DISCOVERY",
                price_sensitivity_detected=False,
            ),
            theme_label="Unknown category",
            related_RQs=[],
        )


def test_insight_card_valid() -> None:
    card = InsightCard(
        insight_id="ins_1",
        statement="Users don't explore pet category due to assortment gaps",
        related_RQs=["RQ2", "RQ8"],
        evidence_count=42,
        source_diversity=2,
        cognitive_barrier_split={"ASSORTMENT_GAP": 0.8, "AWARENESS_DEFICIT": 0.2},
        dominant_funnel_leak_stage="CONSIDERATION",
        confidence_tier="high",
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    assert card.confidence_tier == "high"


def test_compute_record_id_stable() -> None:
    ts = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)
    a = compute_record_id("reddit", "https://reddit.com/a", ts)
    b = compute_record_id("reddit", "https://reddit.com/a", ts)
    assert a == b
    assert len(a) == 64
