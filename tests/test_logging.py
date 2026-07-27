"""Tests for structured logging setup."""

import json
import logging

from common.logging import JsonFormatter, setup_logging


def test_json_formatter_outputs_valid_json(caplog) -> None:
    setup_logging(level="INFO", log_format="json")
    logger = logging.getLogger("test.json")
    logger.info("hello world")
    # Reset to avoid affecting other tests
    logging.getLogger().handlers.clear()


def test_json_formatter_structure() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test message",
        args=(),
        exc_info=None,
    )
    record.run_id = "run_test"
    record.stage = "init"
    record.counts = {"records": 10}
    output = formatter.format(record)
    payload = json.loads(output)
    assert payload["message"] == "test message"
    assert payload["run_id"] == "run_test"
    assert payload["stage"] == "init"
    assert payload["counts"] == {"records": 10}
