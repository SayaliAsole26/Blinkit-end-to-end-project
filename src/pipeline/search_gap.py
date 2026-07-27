"""Stage 8 — Search-gap clustering (Track B): regex filter + HDBSCAN + TF-IDF labels."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from common.config import AppSettings, load_category_vocabulary, load_settings
from common.logging import get_logger
from models.clusters import SearchGapTheme
from models.records import CleanSegment
from pipeline.cluster import run_hdbscan, run_kmeans_fallback

logger = get_logger(__name__)


def compile_search_gap_patterns(patterns: list[str]) -> re.Pattern[str]:
    escaped = [re.escape(p) for p in patterns]
    combined = "|".join(escaped)
    return re.compile(combined, re.IGNORECASE)


def filter_search_gap_segments(
    segments: list[CleanSegment],
    patterns: list[str] | None = None,
) -> list[CleanSegment]:
    """Regex filter for search-gap phrasing (RQ8)."""
    vocab = load_category_vocabulary()
    regex = compile_search_gap_patterns(patterns or vocab.search_gap_patterns)
    matched: list[CleanSegment] = []
    for seg in segments:
        text = f"{seg.normalized_text} {seg.text}".lower()
        if regex.search(text):
            matched.append(seg)
    return matched


def label_cluster_tfidf(
    segments: list[CleanSegment],
    *,
    top_n: int = 5,
) -> tuple[str, list[str]]:
    """Label a search-gap cluster via top TF-IDF terms."""
    texts = [s.normalized_text or s.text for s in segments]
    if len(texts) == 1:
        words = texts[0].lower().split()[:top_n]
        terms = [w for w in words if len(w) > 2][:top_n] or ["search_gap"]
        return " ".join(terms[:3]), terms

    vectorizer = TfidfVectorizer(
        max_features=100,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return "search gap unmet need", ["search", "gap"]

    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf_matrix.mean(axis=0).A1
    ranked_indices = scores.argsort()[::-1]
    top_terms = [feature_names[i] for i in ranked_indices[:top_n] if scores[i] > 0]
    if not top_terms:
        top_terms = ["assortment", "gap"]
    theme_label = " / ".join(top_terms[:3])
    return theme_label, top_terms


@dataclass
class SearchGapResult:
    themes: list[SearchGapTheme]
    matched_segment_count: int = 0
    cluster_count: int = 0

    def summary(self) -> dict:
        return {
            "matched_segment_count": self.matched_segment_count,
            "cluster_count": self.cluster_count,
            "theme_count": len(self.themes),
        }


class SearchGapModule:
    """Track B — parallel search-gap clustering without Groq."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()
        self.cluster_cfg = self.settings.clustering

    def run(
        self,
        segments: list[CleanSegment],
        embeddings: np.ndarray,
    ) -> SearchGapResult:
        matched = filter_search_gap_segments(segments)

        result = SearchGapResult(themes=[], matched_segment_count=len(matched))
        if not matched:
            return result

        id_to_idx = {s.segment_id: i for i, s in enumerate(segments)}
        matched_vectors = np.stack(
            [embeddings[id_to_idx[s.segment_id]] for s in matched],
            axis=0,
        ).astype(np.float32)

        labels = run_hdbscan(
            matched_vectors,
            min_cluster_size=self.cluster_cfg.min_cluster_size,
            metric=self.cluster_cfg.metric,
        )

        noise_pct = (labels == -1).sum() / len(labels) if len(labels) else 0
        if noise_pct > self.cluster_cfg.noise_threshold_pct:
            labels = run_kmeans_fallback(
                matched_vectors,
                min(self.cluster_cfg.kmeans_fallback_k, len(matched)),
            )

        label_to_indices: dict[int, list[int]] = {}
        for i, label in enumerate(labels):
            if label < 0:
                continue
            label_to_indices.setdefault(int(label), []).append(i)

        raw_themes: list[SearchGapTheme] = []
        for label, indices in sorted(label_to_indices.items()):
            cluster_segments = [matched[i] for i in indices]
            cluster_vectors = matched_vectors[indices]
            theme_label, top_terms = label_cluster_tfidf(cluster_segments)

            theme = SearchGapTheme(
                cluster_id=f"sgap_{label:04d}",
                theme_label=theme_label,
                top_terms=top_terms,
                segment_ids=[s.segment_id for s in cluster_segments],
                segment_count=len(cluster_segments),
            )
            raw_themes.append(theme)

        result.themes = raw_themes
        result.cluster_count = len(raw_themes)
        return result
