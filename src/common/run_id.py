"""Generate reproducible run identifiers for ingestion and pipeline jobs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_run_id(prefix: str = "run") -> str:
    """Return a unique run ID: ``{prefix}_{YYYYMMDDTHHMMSS}_{uuid8}``."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


def parse_run_timestamp(run_id: str) -> datetime | None:
    """Extract UTC timestamp embedded in a run ID, if present."""
    parts = run_id.split("_")
    if len(parts) < 2:
        return None
    try:
        return datetime.strptime(parts[1], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
