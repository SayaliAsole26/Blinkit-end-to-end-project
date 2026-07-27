"""Stage 1 — Filter: dedupe, spam, star-only, template families, review-bomb flags."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from common.config import AppSettings, load_settings, resolve_path
from models.records import (
    FilterReason,
    FilterStatus,
    FilteredRecord,
    UnifiedRecord,
)

# Bot / generic spam — exclude from pipeline (raw store unchanged)
_BOT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(click here|free money|earn \$|viagra|casino|buy followers)\b"),
    re.compile(r"(?i)\b(seo service|work from home \$|crypto giveaway)\b"),
    re.compile(r"(.)\1{9,}"),  # same character repeated 10+ times
)

_EMOJI_ONLY = re.compile(
    r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\s\d\W]+$",
    re.UNICODE,
)


def _text_hash(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def _token_set(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 1}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def is_empty_content(raw_text: str) -> bool:
    return not raw_text.strip()


def is_star_only(raw_text: str, rating: int | None) -> bool:
    stripped = raw_text.strip()
    if not stripped and rating is not None:
        return True
    if _EMOJI_ONLY.match(stripped) and len(stripped) <= 8:
        return True
    return False


def is_bot_spam(raw_text: str) -> bool:
    return any(p.search(raw_text) for p in _BOT_PATTERNS)


@dataclass
class FilterAuditEntry:
    record_id: str
    platform: str
    status: str
    reason: str | None = None
    template_family_id: str | None = None
    content_tags: list[str] = field(default_factory=list)


@dataclass
class FilterResult:
    records: list[FilteredRecord]
    audit_entries: list[FilterAuditEntry]
    review_bomb_flagged: bool = False
    review_bomb_window_count: int = 0

    @property
    def included(self) -> list[FilteredRecord]:
        return [r for r in self.records if r.filter_status == FilterStatus.INCLUDED]

    @property
    def excluded(self) -> list[FilteredRecord]:
        return [r for r in self.records if r.filter_status == FilterStatus.EXCLUDED]

    @property
    def star_only(self) -> list[FilteredRecord]:
        return [r for r in self.records if r.filter_status == FilterStatus.STAR_ONLY]

    def summary(self) -> dict:
        return {
            "total_input": len(self.records),
            "included": len(self.included),
            "excluded": len(self.excluded),
            "star_only": len(self.star_only),
            "duplicate_excluded": sum(
                1 for r in self.excluded if r.filter_reason == FilterReason.DUPLICATE
            ),
            "bot_excluded": sum(
                1 for r in self.excluded if r.filter_reason == FilterReason.BOT_TEMPLATE
            ),
            "empty_excluded": sum(
                1 for r in self.excluded if r.filter_reason == FilterReason.EMPTY_CONTENT
            ),
            "template_family_tagged": sum(
                1 for r in self.included if "template_family" in r.content_tags
            ),
            "review_bomb_flagged": self.review_bomb_flagged,
            "review_bomb_window_count": self.review_bomb_window_count,
        }


def _detect_review_bomb(
    records: list[UnifiedRecord],
    settings: AppSettings,
) -> tuple[bool, int]:
    """Flag if any platform exceeds threshold in a sliding time window."""
    window = timedelta(hours=settings.filter.review_bomb_window_hours)
    threshold = settings.filter.review_bomb_threshold
    by_platform: dict[str, list[datetime]] = defaultdict(list)

    for rec in records:
        ts = rec.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        by_platform[rec.platform].append(ts)

    max_count = 0
    flagged = False
    for times in by_platform.values():
        if len(times) < threshold:
            continue
        sorted_times = sorted(times)
        for i, start in enumerate(sorted_times):
            end = start + window
            count = sum(1 for t in sorted_times[i:] if t <= end)
            max_count = max(max_count, count)
            if count >= threshold:
                flagged = True
    return flagged, max_count


def _find_or_create_family(
    token_set: set[str],
    family_registry: list[tuple[set[str], str]],
    threshold: float,
) -> str | None:
    if not token_set:
        return None
    for existing_tokens, family_id in family_registry:
        if jaccard_similarity(token_set, existing_tokens) >= threshold:
            return family_id
    family_id = hashlib.sha256(
        " ".join(sorted(token_set)).encode("utf-8"),
    ).hexdigest()[:16]
    family_registry.append((token_set, family_id))
    return family_id


def _apply_template_family_tags(records: list[FilteredRecord]) -> None:
    """Tag template_family when two or more records share a family id."""
    counts: dict[str, int] = {}
    for rec in records:
        if rec.template_family_id:
            counts[rec.template_family_id] = counts.get(rec.template_family_id, 0) + 1
    for rec in records:
        fid = rec.template_family_id
        if fid and counts.get(fid, 0) >= 2:
            if "template_family" not in rec.content_tags:
                rec.content_tags = [*rec.content_tags, "template_family"]


class FilterModule:
    """Pipeline stage 1 — filter raw UnifiedRecords."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()

    def run(self, records: Iterable[UnifiedRecord]) -> FilterResult:
        record_list = list(records)
        review_bomb_flagged, review_bomb_count = _detect_review_bomb(
            record_list, self.settings
        )

        seen_hashes: set[str] = set()
        family_registry: list[tuple[set[str], str]] = []
        jaccard_threshold = self.settings.filter.near_duplicate_jaccard_threshold
        tag_templates = self.settings.filter.tag_template_families

        filtered: list[FilteredRecord] = []
        audit: list[FilterAuditEntry] = []

        for rec in record_list:
            content_tags: list[str] = []
            template_family_id: str | None = None
            status = FilterStatus.INCLUDED
            reason: FilterReason | None = FilterReason.PASSED

            if is_star_only(rec.raw_text, rec.rating):
                status = FilterStatus.STAR_ONLY
                reason = FilterReason.PASSED
            elif is_empty_content(rec.raw_text):
                status = FilterStatus.EXCLUDED
                reason = FilterReason.EMPTY_CONTENT
            elif is_bot_spam(rec.raw_text):
                status = FilterStatus.EXCLUDED
                reason = FilterReason.BOT_TEMPLATE
            else:
                text_hash = _text_hash(rec.raw_text)
                if text_hash in seen_hashes:
                    status = FilterStatus.EXCLUDED
                    reason = FilterReason.DUPLICATE
                else:
                    seen_hashes.add(text_hash)
                    if tag_templates:
                        tokens = _token_set(rec.raw_text)
                        template_family_id = _find_or_create_family(
                            tokens, family_registry, jaccard_threshold
                        )

            fr = FilteredRecord(
                **rec.model_dump(),
                filter_status=status,
                filter_reason=reason,
                content_tags=content_tags,
                template_family_id=template_family_id,
                review_bomb_flagged=review_bomb_flagged,
            )
            filtered.append(fr)
            audit.append(
                FilterAuditEntry(
                    record_id=rec.record_id,
                    platform=rec.platform,
                    status=status.value,
                    reason=reason.value if reason else None,
                    template_family_id=template_family_id,
                    content_tags=content_tags,
                )
            )

        _apply_template_family_tags(filtered)
        for fr, entry in zip(filtered, audit, strict=True):
            entry.content_tags = list(fr.content_tags)

        return FilterResult(
            records=filtered,
            audit_entries=audit,
            review_bomb_flagged=review_bomb_flagged,
            review_bomb_window_count=review_bomb_count,
        )


def write_filter_audit(
    result: FilterResult,
    pipeline_run_id: str,
    processed_dir: Path | None = None,
) -> Path:
    settings = load_settings()
    out_dir = processed_dir or resolve_path(settings.paths.processed_data)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"filter_audit_{pipeline_run_id}.json"
    payload = {
        "pipeline_run_id": pipeline_run_id,
        "summary": result.summary(),
        "entries": [e.__dict__ for e in result.audit_entries],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
