"""Ingestion layer — source connectors, normalizer, raw store."""

from ingestion.normalizer import normalize_batch, normalize_row
from ingestion.raw_store import RawStore, RawStoreResult
from ingestion.service import IngestionService, IngestionSummary

__all__ = [
    "IngestionService",
    "IngestionSummary",
    "RawStore",
    "RawStoreResult",
    "normalize_batch",
    "normalize_row",
]
