"""Source connector registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ingestion.connectors.app_store import AppStoreConnector
from ingestion.connectors.forum import ForumConnector
from ingestion.connectors.play_store import PlayStoreConnector
from ingestion.connectors.reddit import RedditConnector
from ingestion.connectors.twitter import TwitterConnector

if TYPE_CHECKING:
    from ingestion.connectors.base import BaseConnector

CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "play_store": PlayStoreConnector,
    "app_store": AppStoreConnector,
    "reddit": RedditConnector,
    "twitter": TwitterConnector,
    "forum": ForumConnector,
}

ALL_SOURCES = list(CONNECTOR_REGISTRY.keys())


def get_connector(source: str) -> BaseConnector:
    key = source.lower().replace("-", "_")
    if key not in CONNECTOR_REGISTRY:
        raise ValueError(f"Unknown source: {source}. Choose from {ALL_SOURCES + ['all']}")
    return CONNECTOR_REGISTRY[key]()
