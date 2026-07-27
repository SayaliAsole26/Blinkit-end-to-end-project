"""Append-only raw record store — immutable JSONL per ingestion run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from common.config import load_settings, resolve_path
from models.records import UnifiedRecord


@dataclass
class RawStoreResult:
    written: int = 0
    skipped_duplicates: int = 0
    total_in_run: int = 0
    record_ids: list[str] = field(default_factory=list)


class RawStore:
    """Write-once JSONL store keyed by ingestion_run_id."""

    def __init__(self, base_dir: Path | None = None) -> None:
        settings = load_settings()
        self.base_dir = base_dir or resolve_path(settings.paths.raw_data)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._known_ids: set[str] = set()

    def _path_for_run(self, ingestion_run_id: str) -> Path:
        return self.base_dir / f"{ingestion_run_id}.jsonl"

    def _audit_path(self, ingestion_run_id: str) -> Path:
        return self.base_dir / f"{ingestion_run_id}_audit.json"

    def load_existing_ids(self, ingestion_run_id: str) -> set[str]:
        """Load record IDs already persisted for this run (idempotent re-write)."""
        path = self._path_for_run(ingestion_run_id)
        ids: set[str] = set()
        if not path.exists():
            return ids
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                ids.add(row["record_id"])
        self._known_ids = ids
        return ids

    def append(self, record: UnifiedRecord, ingestion_run_id: str) -> bool:
        """
        Append a record to the run file.
        Returns True if written, False if duplicate record_id in this run.
        """
        if record.record_id in self._known_ids:
            return False
        path = self._path_for_run(ingestion_run_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(record.model_dump_json())
            f.write("\n")
        self._known_ids.add(record.record_id)
        return True

    def write_batch(
        self,
        records: list[UnifiedRecord],
        ingestion_run_id: str,
    ) -> RawStoreResult:
        """Append many records; skip duplicates within the run."""
        self.load_existing_ids(ingestion_run_id)
        result = RawStoreResult()
        for record in records:
            if self.append(record, ingestion_run_id):
                result.written += 1
                result.record_ids.append(record.record_id)
            else:
                result.skipped_duplicates += 1
        result.total_in_run = len(self._known_ids)
        return result

    def read_run(self, ingestion_run_id: str) -> Iterator[UnifiedRecord]:
        """Read all records for an ingestion run."""
        path = self._path_for_run(ingestion_run_id)
        if not path.exists():
            return iter(())
        def _iter() -> Iterator[UnifiedRecord]:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    yield UnifiedRecord.model_validate_json(line)
        return _iter()

    def count(self, ingestion_run_id: str) -> int:
        return sum(1 for _ in self.read_run(ingestion_run_id))

    def write_audit(
        self,
        ingestion_run_id: str,
        summary: dict,
    ) -> Path:
        """Persist ingestion audit summary alongside the JSONL file."""
        audit = {
            "ingestion_run_id": ingestion_run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **summary,
        }
        path = self._audit_path(ingestion_run_id)
        path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
        return path

    def list_runs(self) -> list[str]:
        return sorted(
            p.stem for p in self.base_dir.glob("*.jsonl")
        )

    def read_all(self) -> Iterator[UnifiedRecord]:
        """Read all records across ingestion runs; first occurrence wins per record_id."""
        seen: set[str] = set()
        for run_id in self.list_runs():
            for record in self.read_run(run_id):
                if record.record_id in seen:
                    continue
                seen.add(record.record_id)
                yield record

    def read_ingestion(self, ingestion_run_id: str | None = None) -> Iterator[UnifiedRecord]:
        """Read records for one run, or all unique records if run_id is None."""
        if ingestion_run_id:
            yield from self.read_run(ingestion_run_id)
            return
        yield from self.read_all()
