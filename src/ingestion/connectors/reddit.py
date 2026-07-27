"""Reddit connector — PRAW live search with CSV fallback."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingestion.connectors.base import BaseConnector, resolve_sample_path, with_exponential_backoff

REDDIT_SEARCH_TERMS = [
    "Blinkit",
    "blinkit app",
    "blinkit delivery",
    "blinkit pet",
    "blinkit baby products",
]


class RedditConnector(BaseConnector):
    """
    Fetch Reddit posts/comments via PRAW when credentials exist,
    otherwise load from data/samples/reddit.csv.
    """

    platform = "reddit"

    def __init__(
        self,
        csv_path: Path | None = None,
        search_terms: list[str] | None = None,
        limit_per_term: int = 100,
    ) -> None:
        self.csv_path = csv_path or resolve_sample_path("reddit.csv")
        self.search_terms = search_terms or REDDIT_SEARCH_TERMS
        self.limit_per_term = limit_per_term

    def _fetch_praw(self) -> list[dict[str, Any]]:
        import praw  # optional dependency

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT", "blinkit-insight-engine/0.1.0")
        if not client_id or not client_secret:
            return []

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        rows: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for term in self.search_terms:
            for submission in reddit.subreddit("all").search(term, limit=self.limit_per_term):
                url = f"https://reddit.com{submission.permalink}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                created_at = datetime.fromtimestamp(
                    submission.created_utc, tz=timezone.utc
                )
                rows.append(
                    {
                        "platform": self.platform,
                        "raw_text": submission.selftext or submission.title,
                        "rating": None,
                        "created_at": created_at,
                        "url": url,
                        "metadata": {
                            "source": "reddit_praw",
                            "subreddit": str(submission.subreddit),
                            "search_term": term,
                            "kind": "submission",
                        },
                    }
                )
        return rows

    def _fetch_csv(self) -> list[dict[str, Any]]:
        if not self.csv_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.csv_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                text = row.get("body") or row.get("raw_text") or row.get("content") or ""
                date_raw = row.get("created_at") or row.get("created_utc")
                if date_raw and date_raw.isdigit():
                    created_at = datetime.fromtimestamp(int(date_raw), tz=timezone.utc)
                else:
                    created_at = datetime.fromisoformat(
                        date_raw.replace("Z", "+00:00") if "Z" in date_raw else date_raw
                    )
                url = row.get("permalink") or row.get("url") or ""
                if not url:
                    url = f"https://reddit.com/unknown/{i}"
                if url.startswith("/"):
                    url = f"https://reddit.com{url}"
                rows.append(
                    {
                        "platform": self.platform,
                        "raw_text": text,
                        "rating": None,
                        "created_at": created_at,
                        "url": url,
                        "metadata": {
                            "source": "reddit_csv",
                            "subreddit": row.get("subreddit"),
                            "kind": row.get("kind", "comment"),
                        },
                    }
                )
        return rows

    def fetch(self) -> list[dict[str, Any]]:
        def _load() -> list[dict[str, Any]]:
            try:
                rows = self._fetch_praw()
                if rows:
                    return rows
            except ImportError:
                pass
            except Exception:
                # Rate limit or API error — fall back to CSV
                pass
            return self._fetch_csv()

        return with_exponential_backoff(_load, max_retries=3)
