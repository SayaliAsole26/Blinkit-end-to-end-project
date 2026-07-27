"""Base connector with retry/backoff for rate-limited sources."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_exponential_backoff(
    func: Callable[[], T],
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Retry callable with exponential backoff (for API rate limits)."""
    delay = base_delay
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except retry_on as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            logger.warning(
                "Retry %s/%s after error: %s",
                attempt + 1,
                max_retries,
                exc,
            )
            time.sleep(min(delay, max_delay))
            delay *= 2
    assert last_exc is not None
    raise last_exc


class BaseConnector(ABC):
    """Fetch source-native records as dicts before normalization."""

    platform: str

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Return raw records from the source."""

    def fetch_safe(self) -> list[dict[str, Any]]:
        """Fetch with logging on failure."""
        try:
            rows = self.fetch()
            logger.info(
                "Fetched %s records from %s",
                len(rows),
                self.platform,
            )
            return rows
        except Exception:
            logger.exception("Failed to fetch from %s", self.platform)
            raise


def resolve_sample_path(filename: str) -> Path:
    """Default CSV sample location under data/samples/."""
    from common.config import PROJECT_ROOT

    return PROJECT_ROOT / "data" / "samples" / filename
