"""Stage 2 — Preprocess: record-aware sentence segmentation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable

import pysbd

from common.config import AppSettings, load_settings
from models.records import FilterStatus, FilteredRecord, SentenceSegment

_EMOJI_ONLY = re.compile(
    r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\s\d\W]+$",
    re.UNICODE,
)


def compute_segment_id(record_id: str, sentence_index: int, text: str) -> str:
    payload = f"{record_id}|{sentence_index}|{text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def split_sentences(text: str, lang: str = "en") -> list[str]:
    segmenter = pysbd.Segmenter(language=lang, clean=False)
    return segmenter.segment(text)


def segment_record(record: FilteredRecord, settings: AppSettings) -> list[str]:
    """Return text chunks for one record (whole-record bypass or pysbd split)."""
    raw = record.raw_text.strip()
    if not raw:
        return []

    threshold = settings.preprocess.short_record_char_threshold
    min_chars = settings.preprocess.min_segment_chars

    if len(raw) < threshold:
        chunks = [raw]
    else:
        chunks = split_sentences(raw)

    merged: list[str] = []
    buffer = ""
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or _EMOJI_ONLY.match(chunk):
            continue
        if len(chunk) < min_chars:
            buffer = f"{buffer} {chunk}".strip() if buffer else chunk
            if len(buffer) >= min_chars:
                merged.append(buffer)
                buffer = ""
            continue
        if buffer:
            merged.append(buffer)
            buffer = ""
        merged.append(chunk)
    if buffer and len(buffer) >= min_chars:
        merged.append(buffer)

    return merged


@dataclass
class PreprocessResult:
    segments: list[SentenceSegment] = field(default_factory=list)
    skipped_records: int = 0
    segments_per_record: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict:
        multi = sum(1 for c in self.segments_per_record.values() if c > 1)
        single = sum(1 for c in self.segments_per_record.values() if c == 1)
        return {
            "total_segments": len(self.segments),
            "records_segmented": len(self.segments_per_record),
            "single_segment_records": single,
            "multi_segment_records": multi,
            "skipped_records": self.skipped_records,
        }


class PreprocessModule:
    """Pipeline stage 2 — sentence-level segmentation."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()

    def run(self, records: Iterable[FilteredRecord]) -> PreprocessResult:
        result = PreprocessResult()
        for rec in records:
            if rec.filter_status == FilterStatus.EXCLUDED:
                result.skipped_records += 1
                continue
            if rec.filter_status == FilterStatus.STAR_ONLY:
                result.skipped_records += 1
                continue

            chunks = segment_record(rec, self.settings)
            if not chunks:
                result.skipped_records += 1
                continue

            result.segments_per_record[rec.record_id] = len(chunks)
            for idx, text in enumerate(chunks):
                seg = SentenceSegment(
                    segment_id=compute_segment_id(rec.record_id, idx, text),
                    record_id=rec.record_id,
                    text=text,
                    sentence_index=idx,
                    platform=rec.platform,
                    rating=rec.rating,
                    created_at=rec.created_at,
                    url=rec.url,
                )
                result.segments.append(seg)
        return result
