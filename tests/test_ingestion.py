"""Integration tests for ingestion service and connectors."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ingestion.connectors.app_store import AppStoreConnector
from ingestion.connectors.play_store import PlayStoreConnector
from ingestion.connectors.reddit import RedditConnector
from ingestion.service import IngestionService
from ingestion.raw_store import RawStore
from storage.metadata_db import MetadataDB


@pytest.fixture
def sample_play_csv(tmp_path: Path) -> Path:
    path = tmp_path / "play_store.csv"
    path.write_text(
        "review_text,score,at,review_url,user_name\n"
        '"Great for groceries",5,2024-01-15T10:00:00+00:00,https://play.google.com/r/1,user1\n'
        '"Missing pet food",2,2024-02-20T11:00:00+00:00,https://play.google.com/r/2,user2\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_reddit_csv(tmp_path: Path) -> Path:
    path = tmp_path / "reddit.csv"
    path.write_text(
        "body,created_at,permalink,subreddit,kind\n"
        '"Blinkit vs Amazon for baby products",2024-03-01T09:00:00+00:00,/r/india/comments/a1/test,india,submission\n',
        encoding="utf-8",
    )
    return path


def test_play_store_connector(sample_play_csv: Path) -> None:
    rows = PlayStoreConnector(csv_path=sample_play_csv).fetch()
    assert len(rows) == 2
    assert rows[0]["platform"] == "play_store"
    assert rows[0]["rating"] == 5


def test_reddit_connector_no_rating(sample_reddit_csv: Path) -> None:
    rows = RedditConnector(csv_path=sample_reddit_csv).fetch()
    assert len(rows) == 1
    assert rows[0]["rating"] is None
    assert "reddit.com" in rows[0]["url"]


def test_ingestion_service_end_to_end(tmp_path: Path, sample_play_csv: Path, sample_reddit_csv: Path) -> None:
    # Patch connectors by ingesting sources individually with custom paths
    raw = RawStore(base_dir=tmp_path / "raw")
    db = MetadataDB(db_path=tmp_path / "meta.db")
    service = IngestionService(raw_store=raw, metadata_db=db)

    from ingestion.normalizer import normalize_batch

    run_id = "ingest_integration"
    rows = (
        PlayStoreConnector(csv_path=sample_play_csv).fetch()
        + RedditConnector(csv_path=sample_reddit_csv).fetch()
    )
    records = normalize_batch(rows, run_id)
    result = raw.write_batch(records, run_id)
    assert result.written == 3
    assert raw.count(run_id) == 3

    db.start_ingestion_run(run_id, sources=["play_store", "reddit"])
    db.finish_ingestion_run(run_id, record_count=3)
    assert db.get_ingestion_run(run_id)["record_count"] == 3
