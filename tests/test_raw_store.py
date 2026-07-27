"""Raw store tests — append-only JSONL, immutability, idempotency."""

from datetime import datetime, timezone

from ingestion.raw_store import RawStore
from models.records import UnifiedRecord


def _record(text: str, url: str, run_id: str = "ingest_test") -> UnifiedRecord:
    return UnifiedRecord.build(
        platform="play_store",
        raw_text=text,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url=url,
        ingestion_run_id=run_id,
        rating=4,
    )


def test_write_and_read_run(tmp_path) -> None:
    store = RawStore(base_dir=tmp_path)
    run_id = "run_001"
    records = [_record("Review A", "https://a"), _record("Review B", "https://b")]
    result = store.write_batch(records, run_id)
    assert result.written == 2
    assert store.count(run_id) == 2
    loaded = list(store.read_run(run_id))
    assert len(loaded) == 2
    assert loaded[0].raw_text in ("Review A", "Review B")


def test_skip_duplicate_within_run(tmp_path) -> None:
    store = RawStore(base_dir=tmp_path)
    run_id = "run_dup"
    record = _record("Same", "https://same")
    r1 = store.write_batch([record], run_id)
    r2 = store.write_batch([record], run_id)
    assert r1.written == 1
    assert r2.written == 0
    assert r2.skipped_duplicates == 1
    assert store.count(run_id) == 1


def test_audit_file_written(tmp_path) -> None:
    store = RawStore(base_dir=tmp_path)
    run_id = "run_audit"
    store.write_batch([_record("X", "https://x")], run_id)
    path = store.write_audit(run_id, {"written": 1})
    assert path.exists()
    assert "ingestion_run_id" in path.read_text(encoding="utf-8")


def test_raw_text_unchanged_after_roundtrip(tmp_path) -> None:
    store = RawStore(base_dir=tmp_path)
    run_id = "run_raw"
    original = "  verbatim text with spaces  "
    store.write_batch([_record(original, "https://v")], run_id)
    loaded = next(store.read_run(run_id))
    assert loaded.raw_text == original
