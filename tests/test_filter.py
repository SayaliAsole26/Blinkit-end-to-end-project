"""Phase 2 filter module tests."""

from datetime import datetime, timezone

from models.records import FilterReason, FilterStatus, UnifiedRecord
from pipeline.filter import (
    FilterModule,
    is_bot_spam,
    is_empty_content,
    is_star_only,
    jaccard_similarity,
)


def _record(text: str, **kwargs) -> UnifiedRecord:
    return UnifiedRecord.build(
        platform=kwargs.get("platform", "play_store"),
        raw_text=text,
        created_at=kwargs.get("created_at", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        url=kwargs.get("url", "https://play.google.com/review/1"),
        ingestion_run_id="ingest_test",
        rating=kwargs.get("rating"),
    )


def test_empty_content_excluded() -> None:
    mod = FilterModule()
    result = mod.run([_record("   ")])
    assert len(result.excluded) == 1
    assert result.excluded[0].filter_reason == FilterReason.EMPTY_CONTENT


def test_star_only_retained_not_included() -> None:
    mod = FilterModule()
    result = mod.run([_record("", rating=5)])
    assert len(result.star_only) == 1
    assert result.star_only[0].filter_status == FilterStatus.STAR_ONLY


def test_exact_duplicate_excluded() -> None:
    mod = FilterModule()
    a = _record("Same review text", url="https://play.google.com/a")
    b = _record("Same review text", url="https://play.google.com/b")
    result = mod.run([a, b])
    assert result.summary()["duplicate_excluded"] == 1
    assert len(result.included) == 1


def test_bot_spam_excluded() -> None:
    assert is_bot_spam("Click here for free money now")
    mod = FilterModule()
    result = mod.run([_record("Click here for free money now")])
    assert result.excluded[0].filter_reason == FilterReason.BOT_TEMPLATE


def test_template_family_tagged_not_excluded() -> None:
    mod = FilterModule()
    t1 = _record(
        "Blinkit is great for groceries but I never think to order pet food here.",
        url="https://play.google.com/1",
    )
    t2 = _record(
        "Blinkit is great for groceries but I never think to order baby food here.",
        url="https://play.google.com/2",
    )
    result = mod.run([t1, t2])
    assert len(result.included) == 2
    tagged = [r for r in result.included if "template_family" in r.content_tags]
    assert len(tagged) >= 1


def test_jaccard_similarity() -> None:
    a = {"blinkit", "great", "groceries", "never", "order"}
    b = {"blinkit", "great", "groceries", "never", "order", "pet"}
    assert jaccard_similarity(a, b) > 0.8


def test_is_empty_and_star_only_helpers() -> None:
    assert is_empty_content("  ")
    assert is_star_only("", rating=4)
    assert not is_star_only("Has real text", rating=4)
