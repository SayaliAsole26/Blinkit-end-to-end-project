"""Stage 4 — Embed: BGE-small on embed_text with cache and ChromaDB upsert."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from common.config import AppSettings, load_settings, resolve_path
from models.records import CleanSegment
from storage.embedding_cache import EmbeddingCache
from storage.vector_store import VectorStore


class Embedder(Protocol):
    def encode(self, texts: list[str], batch_size: int) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Lazy-loaded BGE-small encoder."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str], batch_size: int) -> np.ndarray:
        model = self._load()
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.asarray(vectors, dtype=np.float32)


class MockEmbedder:
    """Deterministic mock for tests — 384-dim from text hash."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def encode(self, texts: list[str], batch_size: int) -> np.ndarray:
        del batch_size
        rows = []
        for text in texts:
            seed = abs(hash(text)) % (2**31)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self.dimensions).astype(np.float32)
            vec /= np.linalg.norm(vec) + 1e-9
            rows.append(vec)
        return np.stack(rows, axis=0)


@dataclass
class EmbedResult:
    embedded_count: int = 0
    skipped_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    segment_ids: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total) if total else 0.0
        return {
            "embedded_count": self.embedded_count,
            "skipped_count": self.skipped_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(hit_rate, 4),
        }


class EmbedModule:
    """Pipeline stage 4 — BGE embeddings with cache + vector store."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        cache: EmbeddingCache | None = None,
        vector_store: VectorStore | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.cache = cache or EmbeddingCache()
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or SentenceTransformerEmbedder(
            self.settings.embedding.model
        )

    @property
    def model_version(self) -> str:
        return self.settings.embedding.model

    def _segments_to_embed(self, segments: list[CleanSegment]) -> list[CleanSegment]:
        eligible: list[CleanSegment] = []
        for seg in segments:
            if seg.embed_skipped or not seg.embed_text.strip():
                continue
            eligible.append(seg)
        return eligible

    def run(self, segments: list[CleanSegment]) -> EmbedResult:
        result = EmbedResult()
        eligible = self._segments_to_embed(segments)
        result.skipped_count = len(segments) - len(eligible)

        if not eligible:
            return result

        texts = [s.embed_text for s in eligible]
        cached = self.cache.get_many(texts, self.model_version)

        to_compute: list[tuple[int, CleanSegment, str]] = []
        vectors: list[list[float] | None] = [None] * len(eligible)

        for i, (seg, text) in enumerate(zip(eligible, texts, strict=True)):
            hit = cached.get(text)
            if hit is not None:
                vectors[i] = hit
                result.cache_hits += 1
            else:
                to_compute.append((i, seg, text))
                result.cache_misses += 1

        batch_size = self.settings.embedding.batch_size
        if to_compute:
            miss_texts = [t for _, _, t in to_compute]
            encoded = self.embedder.encode(miss_texts, batch_size=batch_size)
            new_cache: list[tuple[str, list[float]]] = []
            for (idx, _seg, text), row in zip(to_compute, encoded, strict=True):
                vec = row.tolist()
                vectors[idx] = vec
                new_cache.append((text, vec))
            self.cache.put_many(new_cache, self.model_version)

        ids: list[str] = []
        embeddings: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for seg, vec in zip(eligible, vectors, strict=True):
            if vec is None:
                continue
            ids.append(seg.segment_id)
            embeddings.append(vec)
            documents.append(seg.embed_text)
            metadatas.append(
                {
                    "record_id": seg.record_id,
                    "platform": seg.platform,
                    "language": seg.language,
                    "is_logistics_only": seg.is_logistics_only,
                    "category_mentions": seg.category_mentions,
                    "content_tags": seg.content_tags,
                }
            )
            result.segment_ids.append(seg.segment_id)

        self.vector_store.upsert_segments(ids, embeddings, documents, metadatas)
        result.embedded_count = len(ids)
        return result
