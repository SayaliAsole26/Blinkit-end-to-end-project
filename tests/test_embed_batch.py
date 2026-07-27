"""Embed batch shape and mock encoder tests."""

import numpy as np

from models.records import CleanSegment, SentenceSegment
from pipeline.embed import EmbedModule, MockEmbedder
from storage.embedding_cache import EmbeddingCache
from storage.vector_store import VectorStore
from datetime import datetime, timezone


def _clean_segment(embed_text: str, segment_id: str = "s1") -> CleanSegment:
    base = SentenceSegment(
        segment_id=segment_id,
        record_id="r1",
        text=embed_text,
        sentence_index=0,
        platform="play_store",
        rating=4,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        url="https://example.com",
    )
    return CleanSegment(
        **base.model_dump(),
        normalized_text=embed_text,
        embed_text=embed_text,
    )


def test_mock_embedder_output_shape() -> None:
    embedder = MockEmbedder(dimensions=384)
    out = embedder.encode(["hello", "world"], batch_size=64)
    assert out.shape == (2, 384)


def test_embed_module_batch(tmp_path) -> None:
    cache_path = tmp_path / "emb.db"
    chroma_path = tmp_path / "chroma"
    cache = EmbeddingCache(db_path=cache_path)
    store = VectorStore(persist_dir=chroma_path)
    mod = EmbedModule(
        cache=cache,
        vector_store=store,
        embedder=MockEmbedder(dimensions=384),
    )
    segments = [
        _clean_segment("text one", "s1"),
        _clean_segment("text two", "s2"),
        _clean_segment("text three", "s3"),
    ]
    result = mod.run(segments)
    assert result.embedded_count == 3
    assert store.count == 3
    assert result.cache_misses == 3

    # Re-run should hit cache
    result2 = mod.run(segments)
    assert result2.cache_hits == 3
    assert result2.cache_misses == 0


def test_embed_skips_empty_embed_text(tmp_path) -> None:
    cache = EmbeddingCache(db_path=tmp_path / "c.db")
    store = VectorStore(persist_dir=tmp_path / "chroma")
    mod = EmbedModule(cache=cache, vector_store=store, embedder=MockEmbedder())
    seg = _clean_segment("")
    seg.embed_skipped = True
    result = mod.run([seg])
    assert result.embedded_count == 0
    assert result.skipped_count == 1
