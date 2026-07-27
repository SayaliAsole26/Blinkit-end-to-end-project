"""Record ID stability tests."""

from datetime import datetime, timezone

from models.records import UnifiedRecord, compute_record_id


def test_same_input_same_hash() -> None:
    ts = datetime(2024, 5, 10, 8, 30, tzinfo=timezone.utc)
    url = "https://reddit.com/r/india/comments/xyz"
    h1 = compute_record_id("reddit", url, ts)
    h2 = compute_record_id("reddit", url, ts)
    assert h1 == h2


def test_different_url_different_hash() -> None:
    ts = datetime(2024, 5, 10, 8, 30, tzinfo=timezone.utc)
    h1 = compute_record_id("reddit", "https://reddit.com/a", ts)
    h2 = compute_record_id("reddit", "https://reddit.com/b", ts)
    assert h1 != h2


def test_different_platform_different_hash() -> None:
    ts = datetime(2024, 5, 10, 8, 30, tzinfo=timezone.utc)
    url = "https://example.com/review/1"
    h1 = compute_record_id("play_store", url, ts)
    h2 = compute_record_id("app_store", url, ts)
    assert h1 != h2


def test_build_uses_compute_record_id() -> None:
    ts = datetime(2024, 5, 10, 8, 30, tzinfo=timezone.utc)
    url = "https://play.google.com/r/1"
    expected = compute_record_id("play_store", url, ts)
    record = UnifiedRecord.build(
        platform="play_store",
        raw_text="test",
        created_at=ts,
        url=url,
        ingestion_run_id="run",
    )
    assert record.record_id == expected
