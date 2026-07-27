"""Stage 3 — Clean: normalize text, tag content, build embed_text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

import bleach
from rapidfuzz import fuzz, process

from common.config import (
    AppSettings,
    CategoryVocabularyConfig,
    CompetitorAliasesConfig,
    load_category_vocabulary,
    load_competitor_aliases,
    load_settings,
)
from models.records import CleanSegment, FilteredRecord, SentenceSegment

_HINGLISH_MARKERS = (
    " nahi",
    " hai",
    " milta",
    " aati",
    " kya ",
    " acha",
    " bhai",
    " yaar",
    " se ",
    " nhi",
    " nhi ",
)
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_HANDLE = re.compile(r"@(\w+)")
_HTML_TAG = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    cleaned = bleach.clean(text, tags=[], strip=True)
    cleaned = _HTML_TAG.sub("", cleaned)
    return cleaned


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def devanagari_ratio(text: str) -> float:
    if not text:
        return 0.0
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    devanagari_chars = sum(1 for c in chars if _DEVANAGARI.match(c))
    return devanagari_chars / len(chars)


def detect_language(text: str, record_language: str | None) -> str:
    if record_language:
        return record_language
    ratio = devanagari_ratio(text)
    if ratio >= 0.90:
        return "hi"
    lower = text.lower()
    if ratio > 0.05 or any(m in lower for m in _HINGLISH_MARKERS):
        return "hinglish"
    return "en"


def map_categories(text: str, vocab: CategoryVocabularyConfig) -> list[str]:
    lower = text.lower()
    found: set[str] = set()
    threshold = vocab.fuzzy_match_threshold

    for mapping in vocab.mappings:
        for phrase in mapping.phrases:
            if phrase.lower() in lower:
                found.add(mapping.category_id)
                continue
            score = fuzz.partial_ratio(phrase.lower(), lower)
            if score >= threshold:
                found.add(mapping.category_id)

    # Whole-text fuzzy against longest phrases
    for mapping in vocab.mappings:
        choices = {p: mapping.category_id for p in mapping.phrases}
        if not choices:
            continue
        match = process.extractOne(lower, choices.keys(), scorer=fuzz.partial_ratio)
        if match and match[1] >= threshold:
            found.add(mapping.category_id)

    return sorted(found)


def tag_competitors(text: str, aliases: CompetitorAliasesConfig) -> list[str]:
    lower = text.lower()
    found: set[str] = set()
    for entry in aliases.competitors:
        for alias in entry.aliases:
            if alias.lower() in lower:
                found.add(entry.canonical)
                break
    return sorted(found)


def is_logistics_only(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in lower)
    discovery_signals = (
        "never",
        "don't",
        "do not",
        "wish",
        "category",
        "pet",
        "baby",
        "electronics",
        "cross",
        "explore",
        "discover",
    )
    has_discovery = any(s in lower for s in discovery_signals)
    return hits >= 2 and not has_discovery


def has_search_gap_signal(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(p.lower() in lower for p in patterns)


def build_embed_text(
    normalized_text: str,
    *,
    instruction_prefix: str,
    categories: list[str],
    competitors: list[str],
    strip_handles: bool,
) -> str:
    text = normalized_text
    if strip_handles:
        text = _HANDLE.sub(r"\1", text)
    parts = [instruction_prefix]
    if categories:
        parts.append(f"[categories: {', '.join(categories)}] ")
    if competitors:
        parts.append(f"[competitors: {', '.join(competitors)}] ")
    parts.append(text)
    return "".join(parts)


@dataclass
class CleanResult:
    segments: list[CleanSegment] = field(default_factory=list)
    hinglish_included: int = 0
    hinglish_excluded: int = 0

    def summary(self) -> dict:
        return {
            "total_segments": len(self.segments),
            "logistics_only": sum(1 for s in self.segments if s.is_logistics_only),
            "search_gap_tagged": sum(
                1 for s in self.segments if "search_gap" in s.content_tags
            ),
            "hinglish_included": self.hinglish_included,
            "hinglish_excluded": self.hinglish_excluded,
            "embed_skipped": sum(1 for s in self.segments if s.embed_skipped),
        }


class CleanModule:
    """Pipeline stage 3 — normalize and enrich segments."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        category_vocab: CategoryVocabularyConfig | None = None,
        competitor_aliases: CompetitorAliasesConfig | None = None,
        filtered_by_id: dict[str, FilteredRecord] | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.vocab = category_vocab or load_category_vocabulary()
        self.competitors = competitor_aliases or load_competitor_aliases()
        self.filtered_by_id = filtered_by_id or {}

    def clean_segment(
        self,
        seg: SentenceSegment,
        inherited_tags: list[str] | None = None,
        record_language: str | None = None,
    ) -> CleanSegment:
        normalized = normalize_whitespace(strip_html(seg.text))
        language = detect_language(normalized, record_language)
        categories = map_categories(normalized, self.vocab)
        competitor_hits = tag_competitors(normalized, self.competitors)
        logistics = is_logistics_only(normalized, self.vocab.logistics_keywords)

        content_tags = list(inherited_tags or [])
        if has_search_gap_signal(normalized, self.vocab.search_gap_patterns):
            if "search_gap" not in content_tags:
                content_tags.append("search_gap")

        embed_skipped = False
        embed_skip_reason: str | None = None
        threshold = self.settings.clean.hinglish_devanagari_exclude_threshold
        ratio = devanagari_ratio(normalized)
        if ratio > threshold:
            embed_skipped = True
            embed_skip_reason = "devanagari_ratio_exceeded"
            language = "hi"

        embed_text = ""
        if not embed_skipped and self.settings.clean.embed_enrichment:
            embed_text = build_embed_text(
                normalized,
                instruction_prefix=self.settings.embedding.instruction_prefix,
                categories=categories,
                competitors=competitor_hits,
                strip_handles=self.settings.clean.strip_handles_for_embed,
            )

        return CleanSegment(
            **seg.model_dump(),
            normalized_text=normalized,
            embed_text=embed_text,
            category_mentions=categories,
            content_tags=content_tags,
            is_logistics_only=logistics,
            competitor_mentions_raw=competitor_hits,
            language=language,
            embed_skipped=embed_skipped,
            embed_skip_reason=embed_skip_reason,
        )

    def run(
        self,
        segments: Iterable[SentenceSegment],
        filtered_records: Iterable[FilteredRecord] | None = None,
    ) -> CleanResult:
        if filtered_records:
            self.filtered_by_id = {r.record_id: r for r in filtered_records}

        result = CleanResult()
        for seg in segments:
            parent = self.filtered_by_id.get(seg.record_id)
            inherited = list(parent.content_tags) if parent else []
            rec_lang = parent.language if parent else None
            clean = self.clean_segment(seg, inherited_tags=inherited, record_language=rec_lang)
            if clean.language == "hinglish" and not clean.embed_skipped:
                result.hinglish_included += 1
            elif clean.embed_skip_reason == "devanagari_ratio_exceeded":
                result.hinglish_excluded += 1
            result.segments.append(clean)
        return result
