"""Tests for run ID generation."""

import re

from common.run_id import generate_run_id, parse_run_timestamp


RUN_ID_PATTERN = re.compile(
    r"^(run|init|ingest|pipeline)_[0-9]{8}T[0-9]{6}_[0-9a-f]{8}$"
)


def test_generate_run_id_format() -> None:
    run_id = generate_run_id("run")
    assert RUN_ID_PATTERN.match(run_id)


def test_generate_run_id_unique() -> None:
    ids = {generate_run_id() for _ in range(50)}
    assert len(ids) == 50


def test_generate_run_id_custom_prefix() -> None:
    run_id = generate_run_id("ingest")
    assert run_id.startswith("ingest_")


def test_parse_run_timestamp_roundtrip() -> None:
    run_id = generate_run_id("pipeline")
    ts = parse_run_timestamp(run_id)
    assert ts is not None
    assert ts.tzinfo is not None


def test_parse_run_timestamp_invalid() -> None:
    assert parse_run_timestamp("invalid") is None
