"""ChromaDB vector store for segment embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from common.config import load_settings, resolve_path


COLLECTION_NAME = "segments"


class VectorStore:
    """Persistent ChromaDB collection for CleanSegment embeddings."""

    def __init__(
        self,
        persist_dir: Path | None = None,
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        settings = load_settings()
        self.persist_dir = persist_dir or resolve_path(
            f"{settings.paths.processed_data}/chroma"
        )
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self._collection.count()

    def upsert_segments(
        self,
        segment_ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> int:
        if not segment_ids:
            return 0
        # Chroma metadata values must be str, int, float, or bool
        clean_meta: list[dict[str, Any]] = []
        for meta in metadatas:
            clean_meta.append(
                {
                    k: (
                        ", ".join(v)
                        if isinstance(v, list)
                        else v
                    )
                    for k, v in meta.items()
                }
            )
        self._collection.upsert(
            ids=segment_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=clean_meta,
        )
        return len(segment_ids)

    def get_by_ids(self, segment_ids: list[str]) -> dict:
        if not segment_ids:
            return {"ids": [], "embeddings": [], "metadatas": []}
        return self._collection.get(ids=segment_ids, include=["embeddings", "metadatas"])

    def reset_collection(self) -> None:
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
