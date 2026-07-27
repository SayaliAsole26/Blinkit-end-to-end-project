"""API endpoint tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    repo_data = Path(__file__).resolve().parents[1] / "data"
    monkeypatch.setenv("BLINKIT_DATA_DIR", str(repo_data))
    monkeypatch.setenv("INSIGHTS_RUN_ID", "run_phase4_final")
    return TestClient(app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "/api/overview" in body["endpoints"]


def test_overview(client):
    res = client.get("/api/overview")
    assert res.status_code == 200
    body = res.json()
    assert body["insight_count"] > 0
    assert "barrier_distribution" in body
    assert "high_confidence_pct" in body
    assert "data_collection" in body
    assert body["data_collection"].get("duration_days", 0) > 0
    assert "sentiment_split" not in body


def test_insights_pagination(client):
    res = client.get("/api/insights?page=1&page_size=5")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 5
    assert body["total"] > 0


def test_no_sentiment_in_insight(client):
    res = client.get("/api/insights?page=1&page_size=1")
    item = res.json()["items"][0]
    assert "cognitive_barrier_split" in item
    assert "sentiment_split" not in item
