"""Stage 10 — Insight synthesis from cluster analyses and search-gap themes."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from common.config import AppSettings, load_settings, load_taxonomy, resolve_path
from models.clusters import SearchGapTheme
from models.friction import ClusterAnalysis
from models.insights import CompetitorMention, InsightCard
from models.records import CleanSegment

RECENCY_LAMBDA = 0.05


@dataclass
class SynthesisResult:
    insight_cards: list[InsightCard] = field(default_factory=list)
    cards_path: str | None = None

    def summary(self) -> dict:
        tiers = Counter(c.confidence_tier for c in self.insight_cards)
        return {
            "insight_count": len(self.insight_cards),
            "confidence_tiers": dict(tiers),
            "stale_count": sum(1 for c in self.insight_cards if c.is_stale),
        }


def load_analyses(path: Path) -> list[ClusterAnalysis]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ClusterAnalysis.model_validate(item) for item in data]


def load_search_gap_themes(path: Path) -> list[SearchGapTheme]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SearchGapTheme.model_validate(item) for item in data]


def load_cluster_memberships(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["cluster_id"]: item["segment_ids"] for item in data}


def _insight_id(theme: str, barrier: str) -> str:
    payload = f"{theme}|{barrier}".lower()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def paraphrase_snippet(text: str) -> str:
    """Transform evidence text — never return verbatim source (copyright)."""
    t = text.strip()
    if not t:
        return "User feedback about cross-category shopping friction."

    replacements = [
        (r"\bBlinkit\b", "the quick-commerce app"),
        (r"\bAmazon\b", "a major online marketplace"),
        (r"\bZepto\b", "a rival delivery service"),
        (r"\bInstamart\b", "a competing grocery app"),
        (r"\bNykaa\b", "a specialty retail platform"),
    ]
    result = t
    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)

    if result.lower().strip() == t.lower().strip():
        lowered = t[0].lower() + t[1:] if len(t) > 1 else t.lower()
        result = f"Reviewers mention that {lowered.rstrip('.')}."

    if len(result) > 220:
        result = result[:217] + "..."
    return result


def _barrier_split(counts: Counter[str]) -> dict[str, float]:
    total = sum(counts.values())
    if total == 0:
        return {}
    return {k: round(v / total, 4) for k, v in counts.items()}


def source_diversity_weight(platform_count: int) -> float:
    return 1.0 + 0.25 * max(0, platform_count - 1)


def recency_decay(latest: datetime, *, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    months = max(0.0, (now - latest).days / 30.44)
    return math.exp(-RECENCY_LAMBDA * months)


def assign_confidence_tier(
    source_diversity: int,
    agreement_rate: float | None = None,
) -> str:
    if agreement_rate is not None and agreement_rate >= 0.7 and source_diversity >= 2:
        return "high"
    if source_diversity >= 2:
        return "high"
    if source_diversity >= 1 and (agreement_rate is None or agreement_rate >= 0.5):
        return "medium"
    return "low"


def build_statement(
    theme_label: str,
    barrier: str,
    funnel: str,
    evidence_count: int,
    source_diversity: int,
) -> str:
    taxonomy = load_taxonomy()
    barrier_label = barrier
    for item in taxonomy.cognitive_barriers:
        if item.id == barrier:
            barrier_label = item.label or barrier
            break
    return (
        f"{theme_label}: {evidence_count} feedback mentions suggest "
        f"{barrier_label} as a barrier at the {funnel.replace('_', ' ').title()} stage, "
        f"observed across {source_diversity} platform(s)."
    )


@dataclass
class _InsightGroup:
    theme_label: str
    barrier: str
    analyses: list[ClusterAnalysis] = field(default_factory=list)
    segment_ids: set[str] = field(default_factory=set)
    cluster_ids: list[str] = field(default_factory=list)


class SynthesisModule:
    """Aggregate cluster + search-gap outputs into ranked InsightCard objects."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()
        self.stale_months = self.settings.validation.stale_months

    def run(
        self,
        analyses: list[ClusterAnalysis],
        cluster_members: dict[str, list[str]],
        segments: list[CleanSegment],
        search_gap_themes: list[SearchGapTheme],
        *,
        agreement_by_cluster: dict[str, float] | None = None,
    ) -> SynthesisResult:
        seg_by_id = {s.segment_id: s for s in segments}
        groups: dict[tuple[str, str], _InsightGroup] = {}

        for analysis in analyses:
            barrier = analysis.friction.user_cognitive_barrier
            key = (analysis.theme_label.strip().lower(), barrier)
            if key not in groups:
                groups[key] = _InsightGroup(
                    theme_label=analysis.theme_label,
                    barrier=barrier,
                )
            group = groups[key]
            group.analyses.append(analysis)
            group.cluster_ids.append(analysis.cluster_id)
            for sid in cluster_members.get(analysis.cluster_id, []):
                group.segment_ids.add(sid)

        cards: list[InsightCard] = []
        now = datetime.now(timezone.utc)

        for _, group in groups.items():
            card = self._build_discovery_card(
                group, seg_by_id, now, agreement_by_cluster
            )
            if card:
                cards.append(card)

        for theme in search_gap_themes:
            card = self._build_search_gap_card(theme, seg_by_id, now)
            if card:
                cards.append(card)

        cards.sort(
            key=lambda c: (
                c.evidence_count
                * source_diversity_weight(c.source_diversity)
                * (1.0 if not c.is_stale else 0.5)
            ),
            reverse=True,
        )
        return SynthesisResult(insight_cards=cards)

    def _build_discovery_card(
        self,
        group: _InsightGroup,
        seg_by_id: dict[str, CleanSegment],
        now: datetime,
        agreement_by_cluster: dict[str, float] | None,
    ) -> InsightCard | None:
        member_segments = [seg_by_id[sid] for sid in group.segment_ids if sid in seg_by_id]
        if not member_segments:
            return None

        platforms = {s.platform for s in member_segments}
        barrier_counts = Counter(a.friction.user_cognitive_barrier for a in group.analyses)
        funnel_counts = Counter(a.friction.funnel_leak_stage for a in group.analyses)
        dominant_funnel = funnel_counts.most_common(1)[0][0]

        competitor_roll: Counter[tuple[str, str]] = Counter()
        for analysis in group.analyses:
            entity = analysis.friction.competitor_entity
            advantage = analysis.friction.competitor_advantage
            if entity and advantage:
                competitor_roll[(entity, advantage)] += 1

        latest = max(s.created_at for s in member_segments)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        months_old = (now - latest).days / 30.44
        is_stale = months_old > self.stale_months

        avg_agreement = None
        if agreement_by_cluster:
            rates = [
                agreement_by_cluster[cid]
                for cid in group.cluster_ids
                if cid in agreement_by_cluster
            ]
            if rates:
                avg_agreement = sum(rates) / len(rates)

        rqs: list[str] = []
        for a in group.analyses:
            rqs.extend(a.related_RQs)
        unique_rqs = list(dict.fromkeys(rqs))

        segment_rel: list[str] = []
        for a in group.analyses:
            segment_rel.extend(a.segment_relevance)
        unique_seg_rel = list(dict.fromkeys(segment_rel))

        snippets: list[str] = []
        for seg in member_segments[:5]:
            para = paraphrase_snippet(seg.normalized_text or seg.text)
            if para not in snippets:
                snippets.append(para)
            if len(snippets) >= 3:
                break

        return InsightCard(
            insight_id=_insight_id(group.theme_label, group.barrier),
            statement=build_statement(
                group.theme_label,
                group.barrier,
                dominant_funnel,
                len(member_segments),
                len(platforms),
            ),
            related_RQs=unique_rqs or ["RQ6"],
            theme_tags=[group.theme_label],
            evidence_count=len(member_segments),
            source_diversity=len(platforms),
            cognitive_barrier_split=_barrier_split(barrier_counts),
            dominant_funnel_leak_stage=dominant_funnel,
            competitor_mentions=[
                CompetitorMention(entity=e, advantage=a, count=c)
                for (e, a), c in competitor_roll.most_common(5)
            ],
            example_snippets=snippets[:3],
            confidence_tier=assign_confidence_tier(len(platforms), avg_agreement),
            segment_relevance=unique_seg_rel,
            is_stale=is_stale,
            taxonomy_version=self.settings.taxonomy_version,
            created_at=now,
        )

    def _build_search_gap_card(
        self,
        theme: SearchGapTheme,
        seg_by_id: dict[str, CleanSegment],
        now: datetime,
    ) -> InsightCard | None:
        member_segments = [seg_by_id[sid] for sid in theme.segment_ids if sid in seg_by_id]
        if not member_segments:
            return None

        platforms = {s.platform for s in member_segments}
        latest = max(s.created_at for s in member_segments)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        months_old = (now - latest).days / 30.44

        snippets = [
            paraphrase_snippet(s.normalized_text or s.text)
            for s in member_segments[:3]
        ]

        return InsightCard(
            insight_id=_insight_id(theme.theme_label, "ASSORTMENT_GAP"),
            statement=(
                f"Search-gap theme '{theme.theme_label}': {len(member_segments)} users "
                f"report unmet product needs (assortment gap) across {len(platforms)} platform(s)."
            ),
            related_RQs=["RQ8"],
            theme_tags=[theme.theme_label, *theme.top_terms[:2]],
            evidence_count=len(member_segments),
            source_diversity=len(platforms),
            cognitive_barrier_split={"ASSORTMENT_GAP": 1.0},
            dominant_funnel_leak_stage="CONSIDERATION",
            example_snippets=snippets[:3],
            confidence_tier=assign_confidence_tier(len(platforms)),
            segment_relevance=[],
            is_stale=months_old > self.stale_months,
            taxonomy_version=self.settings.taxonomy_version,
            created_at=now,
        )
