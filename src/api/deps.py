"""Shared API dependencies."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from common.config import load_settings, resolve_path


@lru_cache(maxsize=1)
def get_insights_run_id() -> str:
    return os.environ.get("INSIGHTS_RUN_ID", "run_phase4_final")


def get_data_dir() -> Path:
    override = os.environ.get("BLINKIT_DATA_DIR")
    if override:
        return Path(override)
    settings = load_settings()
    return resolve_path(settings.paths.insights).parent


def insights_path() -> Path:
    run_id = get_insights_run_id()
    return get_data_dir() / "insights" / f"insights_{run_id}.json"


def validation_path() -> Path:
    run_id = get_insights_run_id()
    return get_data_dir() / "processed" / f"validation_{run_id}.json"


def summary_path() -> Path:
    run_id = get_insights_run_id()
    return get_data_dir() / "processed" / f"synthesize_validate_summary_{run_id}.json"


def load_json(path: Path) -> list | dict:
    if not path.exists():
        return [] if "insights" in path.name else {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)
