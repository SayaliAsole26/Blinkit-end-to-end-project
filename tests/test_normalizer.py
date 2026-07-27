"""Normalizer tests — connector rows to UnifiedRecord."""

from datetime import datetime, timezone

from ingestion.normalizer import normalize_batch, normalize_row


def test_normalize_play_store_row() -> None:
    row = {
        "platform": "play_store",
        "raw_text": "Missing pet food brands",
        "rating": 3,
        "created_at": datetime(2024, 2, 1, tzinfo=timezone.utc),
        "url": "https://play.google.com/review/99",
        "metadata": {"source": "play_store_csv"},
    }
    record = normalize_row(row, "ingest_001")
    assert record.platform == "play_store"
    assert record.raw_text == "Missing pet food brands"
    assert record.rating == 3
    assert record.ingestion_run_id == "ingest_001"
    assert record.record_id


def test_normalize_reddit_null_rating_flagged() -> None:
    row = {
        "platform": "reddit",
        "raw_text": "Blinkit vs Zepto for personal care?",
        "rating": None,
        "created_at": datetime(2024, 2, 1, tzinfo=timezone.utc),
        "url": "https://reddit.com/r/india/abc",
        "metadata": {"source": "reddit_csv"},
    }
    record = normalize_row(row, "ingest_001")
    assert record.rating is None
    assert record.metadata.get("rating_missing") is True


def test_normalize_batch_dedupes() -> None:
    ts = datetime(2024, 2, 1, tzinfo=timezone.utc)
    row = {
        "platform": "app_store",
        "raw_text": "Same review",
        "rating": 4,
        "created_at": ts,
        "url": "https://apps.apple.com/1",
        "metadata": {},
    }
    records = normalize_batch([row, row], "ingest_001")
    assert len(records) == 1


def test_raw_text_preserved_verbatim() -> None:
    raw = "  Hinglish text: Blinkit pe baby products nahi milte  "
    row = {
        "platform": "play_store",
        "raw_text": raw,
        "rating": 2,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "url": "https://play.google.com/r/1",
        "metadata": {},
    }
    record = normalize_row(row, "run")
    assert record.raw_text == raw
