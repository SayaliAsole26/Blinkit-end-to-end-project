"""Tests for metadata database schema stub."""

from pathlib import Path

import pytest

from storage.metadata_db import MetadataDB


@pytest.fixture
def db(tmp_path: Path) -> MetadataDB:
    return MetadataDB(db_path=tmp_path / "test_metadata.db")


def test_schema_created(db: MetadataDB) -> None:
    assert db.db_path.exists()


def test_ingestion_run_lifecycle(db: MetadataDB) -> None:
    run_id = "ingest_20260101T120000_abcd1234"
    db.start_ingestion_run(run_id, sources=["play_store", "reddit"])
    db.finish_ingestion_run(run_id, record_count=1000, status="completed")

    row = db.get_ingestion_run(run_id)
    assert row is not None
    assert row["record_count"] == 1000
    assert row["status"] == "completed"
    assert row["finished_at"] is not None


def test_pipeline_stage_tracking(db: MetadataDB) -> None:
    run_id = "run_20260101T120000_abcd1234"
    db.start_pipeline_stage(run_id, "clean_embed", counts={"segments": 5000})
    db.finish_pipeline_stage(run_id, "clean_embed", counts={"segments": 5000, "embedded": 5000})

    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ? AND stage = ?",
            (run_id, "clean_embed"),
        ).fetchone()
    assert row is not None
    assert row["status"] == "completed"


def test_list_ingestion_runs(db: MetadataDB) -> None:
    for i in range(3):
        db.start_ingestion_run(f"run_{i}")
        db.finish_ingestion_run(f"run_{i}", record_count=i * 100)
    runs = db.list_ingestion_runs(limit=10)
    assert len(runs) == 3
