"""Integration test for clean_embed pipeline."""

from datetime import datetime, timezone
from pathlib import Path

from common.config import load_settings
from ingestion.raw_store import RawStore
from models.records import UnifiedRecord
from pipeline.clean_embed import CleanEmbedPipeline
from pipeline.embed import MockEmbedder
from storage.embedding_cache import EmbeddingCache
from storage.vector_store import VectorStore


def test_clean_embed_e2e(tmp_path: Path, monkeypatch) -> None:
    settings = load_settings()
    raw_dir = tmp_path / "raw"
    proc_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)
    db_path = tmp_path / "metadata.db"
    cache_path = tmp_path / "emb.db"
    chroma_path = tmp_path / "chroma"

    def _resolve(rel: str) -> Path:
        if "raw" in rel and "processed" not in rel:
            return raw_dir
        if rel.startswith("data/processed"):
            suffix = rel.removeprefix("data/processed/").removeprefix("data/processed")
            if suffix:
                target = proc_dir / suffix
                target.parent.mkdir(parents=True, exist_ok=True)
                return target
            return proc_dir
        if "metadata" in rel:
            return db_path
        return tmp_path / Path(rel).name

    for mod in (
        "common.config",
        "ingestion.raw_store",
        "pipeline.clean_embed",
        "pipeline.filter",
        "storage.metadata_db",
    ):
        monkeypatch.setattr(f"{mod}.resolve_path", _resolve)

    store = RawStore(base_dir=raw_dir)
    records = [
        UnifiedRecord.build(
            platform="play_store",
            raw_text="Never explored pet food on Blinkit.",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            url="https://play.google.com/1",
            ingestion_run_id="ingest_test",
            rating=4,
        ),
        UnifiedRecord.build(
            platform="reddit",
            raw_text="Delivery late again, rider was rude.",
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
            url="https://reddit.com/1",
            ingestion_run_id="ingest_test",
        ),
    ]
    store.write_batch(records, "ingest_test")

    pipeline = CleanEmbedPipeline(
        settings=settings,
        embedder=MockEmbedder(dimensions=384),
        cache=EmbeddingCache(db_path=cache_path),
        vector_store=VectorStore(persist_dir=chroma_path),
    )

    result = pipeline.run("pipeline_test_001", ingestion_run_id="ingest_test")
    assert result.total_input_records == 2
    assert result.embed_summary["embedded_count"] >= 1
    assert result.filter_audit_path is not None
    assert Path(result.segments_path).exists()
