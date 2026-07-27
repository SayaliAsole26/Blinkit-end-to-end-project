"""Embedding cache tests."""

from pathlib import Path

from storage.embedding_cache import EmbeddingCache, cache_key


def test_cache_key_stable() -> None:
    a = cache_key("hello world", "model-v1")
    b = cache_key("hello world", "model-v1")
    c = cache_key("hello world", "model-v2")
    assert a == b
    assert a != c


def test_cache_hit_and_miss(tmp_path: Path) -> None:
    db = tmp_path / "cache.db"
    cache = EmbeddingCache(db_path=db)
    model = "test-model"
    text = "Represent feedback: pet supplies"
    vec = [0.1] * 384

    assert cache.get(text, model) is None
    cache.put(text, model, vec)
    hit = cache.get(text, model)
    assert hit is not None
    assert len(hit) == 384
    assert abs(hit[0] - 0.1) < 1e-6


def test_cache_miss_on_text_change(tmp_path: Path) -> None:
    db = tmp_path / "cache.db"
    cache = EmbeddingCache(db_path=db)
    model = "test-model"
    cache.put("text a", model, [0.0] * 8)
    assert cache.get("text b", model) is None


def test_get_many_partial_hits(tmp_path: Path) -> None:
    db = tmp_path / "cache.db"
    cache = EmbeddingCache(db_path=db)
    model = "test-model"
    cache.put("one", model, [1.0] * 4)
    result = cache.get_many(["one", "two"], model)
    assert result["one"] is not None
    assert result["two"] is None
