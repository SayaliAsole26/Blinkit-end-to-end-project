"""Tests for search-gap track — regex filter + TF-IDF, zero Groq."""

from datetime import datetime, timezone

import numpy as np

from models.records import CleanSegment, SentenceSegment
from pipeline.search_gap import (
    SearchGapModule,
    filter_search_gap_segments,
    label_cluster_tfidf,
)


def _segment(text: str, segment_id: str) -> CleanSegment:
    base = SentenceSegment(
        segment_id=segment_id,
        record_id=f"rec_{segment_id}",
        text=text,
        sentence_index=0,
        platform="play_store",
        rating=4,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url=f"https://example.com/{segment_id}",
    )
    return CleanSegment(
        **base.model_dump(),
        normalized_text=text,
        embed_text=text,
    )


def test_regex_filter_matches_search_gap_phrases() -> None:
    segments = [
        _segment("Wish they had dog food brands", "s1"),
        _segment("Great delivery speed", "s2"),
        _segment("Couldn't find diapers on Blinkit", "s3"),
        _segment("Love the groceries section", "s4"),
    ]
    matched = filter_search_gap_segments(segments)
    ids = {s.segment_id for s in matched}
    assert ids == {"s1", "s3"}


def test_tfidf_label_produces_terms() -> None:
    segments = [
        _segment("Couldn't find organic dog food brands", "s1"),
        _segment("Missing premium dog food options", "s2"),
        _segment("Don't have my usual dog food brand", "s3"),
    ]
    label, terms = label_cluster_tfidf(segments)
    assert label
    assert len(terms) >= 1


def test_search_gap_module_zero_groq(tmp_path, monkeypatch) -> None:
    """Search-gap track produces themes without invoking Groq."""
    groq_called = {"count": 0}

    def _fake_groq(*args, **kwargs):
        groq_called["count"] += 1
        raise AssertionError("Groq should not be called in search-gap track")

    monkeypatch.setattr("pipeline.cluster_label.GroqClient", _fake_groq)

    segments = [
        _segment("Wish they had stationery notebooks on Blinkit", f"sg{i}")
        for i in range(6)
    ] + [
        _segment("Couldn't find kids toys on the app", f"sg{i + 6}")
        for i in range(6)
    ]

    dim = 384
    vectors = np.stack([
        np.random.default_rng(i).standard_normal(dim).astype(np.float32)
        for i in range(len(segments))
    ])
    for i, row in enumerate(vectors):
        vectors[i] = row / (np.linalg.norm(row) + 1e-9)

    mod = SearchGapModule()
    result = mod.run(segments, vectors)

    assert groq_called["count"] == 0
    assert result.matched_segment_count == len(segments)
    assert result.cluster_count >= 1
    assert all(t.related_RQs == ["RQ8"] for t in result.themes)
    assert all(t.cognitive_barrier == "ASSORTMENT_GAP" for t in result.themes)
