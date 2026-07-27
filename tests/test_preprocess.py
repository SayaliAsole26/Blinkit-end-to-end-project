"""Phase 2 preprocess module tests."""

from datetime import datetime, timezone

from common.config import load_settings
from models.records import FilterReason, FilterStatus, FilteredRecord, UnifiedRecord
from pipeline.preprocess import PreprocessModule, segment_record


def _filtered(text: str, url: str = "https://example.com/1") -> FilteredRecord:
    base = UnifiedRecord.build(
        platform="twitter",
        raw_text=text,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url=url,
        ingestion_run_id="ingest_test",
    )
    return FilteredRecord(
        **base.model_dump(),
        filter_status=FilterStatus.INCLUDED,
        filter_reason=FilterReason.PASSED,
    )


def test_short_record_single_segment() -> None:
    settings = load_settings()
    rec = _filtered("Never explored pet supplies on Blinkit.")
    chunks = segment_record(rec, settings)
    assert len(chunks) == 1
    assert chunks[0] == rec.raw_text


def test_long_record_splits() -> None:
    settings = load_settings()
    long_text = " ".join(
        [
            "Blinkit works well for daily groceries and snacks.",
            "I never think to browse electronics or personal care categories.",
            "Maybe the app should surface cross-category suggestions more often.",
            "Delivery is usually fast in my area which keeps me loyal to groceries only.",
        ]
        * 3
    )
    assert len(long_text) >= settings.preprocess.short_record_char_threshold
    rec = _filtered(long_text)
    chunks = segment_record(rec, settings)
    assert len(chunks) >= 2


def test_preprocess_skips_excluded() -> None:
    base = UnifiedRecord.build(
        platform="reddit",
        raw_text="excluded",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://reddit.com/x",
        ingestion_run_id="ingest_test",
    )
    excluded = FilteredRecord(
        **base.model_dump(),
        filter_status=FilterStatus.EXCLUDED,
        filter_reason=FilterReason.DUPLICATE,
    )
    result = PreprocessModule().run([excluded])
    assert result.segments == []
    assert result.skipped_records == 1


def test_metadata_retained_on_segments() -> None:
    rec = _filtered("Short review about baby products.", url="https://twitter.com/status/1")
    rec = FilteredRecord(**{**rec.model_dump(), "rating": 3})
    result = PreprocessModule().run([rec])
    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.platform == "twitter"
    assert seg.rating == 3
    assert seg.url == "https://twitter.com/status/1"
    assert seg.record_id == rec.record_id
