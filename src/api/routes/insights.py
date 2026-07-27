"""Insight and chart API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.deps import get_insights_run_id, insights_path, load_json, summary_path, validation_path

router = APIRouter(prefix="/api", tags=["insights"])

BARRIER_LABELS = {
    "AWARENESS_DEFICIT": "Awareness Deficit",
    "AUTHENTICITY_DISTRUST": "Authenticity Distrust",
    "ASSORTMENT_GAP": "Assortment Gap",
    "CONVENIENCE_MISMATCH": "Convenience Mismatch",
    "RETURN_POLICY_ANXIETY": "Return Policy Anxiety",
    "NONE_GROCERY_LOYAL": "Grocery Loyal",
}

FUNNEL_STAGES = ["DISCOVERY", "CONSIDERATION", "CONVERSION", "POST_PURCHASE_RETENTION"]


def _load_insights() -> list[dict[str, Any]]:
    data = load_json(insights_path())
    if not isinstance(data, list):
        return []
    return data


def _filter_insights(
    items: list[dict[str, Any]],
    *,
    rq: str | None = None,
    theme: str | None = None,
    barrier: str | None = None,
    funnel_stage: str | None = None,
    confidence: str | None = None,
    segment: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    out = items
    if rq:
        out = [i for i in out if rq in i.get("related_RQs", [])]
    if theme:
        needle = theme.lower()
        out = [i for i in out if any(needle in t.lower() for t in i.get("theme_tags", []))]
    if barrier:
        out = [
            i
            for i in out
            if barrier in i.get("cognitive_barrier_split", {})
            or i.get("cognitive_barrier_split", {}).get(barrier, 0) > 0
        ]
    if funnel_stage:
        out = [i for i in out if i.get("dominant_funnel_leak_stage") == funnel_stage]
    if confidence:
        out = [i for i in out if i.get("confidence_tier") == confidence]
    if segment:
        needle = segment.lower()
        out = [
            i
            for i in out
            if any(needle in s.lower() for s in i.get("segment_relevance", []))
        ]
    if q:
        needle = q.lower()
        out = [i for i in out if needle in i.get("statement", "").lower()]
    return out


@router.get("/overview")
def overview() -> dict[str, Any]:
    insights = _load_insights()
    summary = load_json(summary_path())
    validation = load_json(validation_path())

    barrier_totals: dict[str, float] = {}
    funnel_totals: dict[str, int] = {}
    for card in insights:
        stage = card.get("dominant_funnel_leak_stage", "UNKNOWN")
        funnel_totals[stage] = funnel_totals.get(stage, 0) + 1
        for barrier, weight in card.get("cognitive_barrier_split", {}).items():
            barrier_totals[barrier] = barrier_totals.get(barrier, 0.0) + float(weight)

    synth = summary.get("synthesis", {}) if isinstance(summary, dict) else {}
    val = validation.get("validation_run", {}) if isinstance(validation, dict) else {}
    tiers = synth.get("confidence_tiers", {})
    high_count = tiers.get("high", 0)
    total_insights = len(insights) or 1

    return {
        "run_id": get_insights_run_id(),
        "insight_count": len(insights),
        "evidence_mentions": sum(i.get("evidence_count", 0) for i in insights),
        "confidence_tiers": tiers,
        "high_confidence_count": high_count,
        "high_confidence_pct": round(high_count / total_insights * 100, 1),
        "max_source_diversity": max((i.get("source_diversity", 0) for i in insights), default=0),
        "stale_count": synth.get("stale_count", sum(1 for i in insights if i.get("is_stale"))),
        "agreement_rate": val.get("agreement_rate"),
        "barrier_distribution": barrier_totals,
        "funnel_distribution": funnel_totals,
        "top_insights": sorted(insights, key=lambda x: x.get("evidence_count", 0), reverse=True)[:5],
    }


@router.get("/insights")
def list_insights(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    rq: str | None = None,
    theme: str | None = None,
    barrier: str | None = None,
    funnel_stage: str | None = None,
    confidence: str | None = None,
    segment: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    filtered = _filter_insights(
        _load_insights(),
        rq=rq,
        theme=theme,
        barrier=barrier,
        funnel_stage=funnel_stage,
        confidence=confidence,
        segment=segment,
        q=q,
    )
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": filtered[start:end],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
    }


@router.get("/insights/{insight_id}")
def get_insight(insight_id: str) -> dict[str, Any]:
    for card in _load_insights():
        if card.get("insight_id") == insight_id:
            return card
    raise HTTPException(status_code=404, detail="Insight not found")


@router.get("/charts/barriers")
def chart_barriers() -> dict[str, Any]:
    insights = _load_insights()
    by_barrier: dict[str, int] = {}
    for card in insights:
        split = card.get("cognitive_barrier_split", {})
        if not split:
            continue
        dominant = max(split, key=lambda k: split[k])
        by_barrier[dominant] = by_barrier.get(dominant, 0) + 1
    return {
        "labels": [BARRIER_LABELS.get(k, k) for k in by_barrier],
        "counts": list(by_barrier.values()),
        "raw": by_barrier,
    }


@router.get("/charts/funnel")
def chart_funnel() -> dict[str, Any]:
    insights = _load_insights()
    counts = {stage: 0 for stage in FUNNEL_STAGES}
    for card in insights:
        stage = card.get("dominant_funnel_leak_stage")
        if stage in counts:
            counts[stage] += 1
    return {"stages": FUNNEL_STAGES, "counts": [counts[s] for s in FUNNEL_STAGES], "raw": counts}


@router.get("/charts/competitors")
def chart_competitors() -> dict[str, Any]:
    insights = _load_insights()
    matrix: dict[str, dict[str, int]] = {}
    for card in insights:
        for mention in card.get("competitor_mentions", []):
            entity = mention.get("entity", "Unknown")
            advantage = mention.get("advantage", "UNKNOWN")
            matrix.setdefault(entity, {})
            matrix[entity][advantage] = matrix[entity].get(advantage, 0) + int(mention.get("count", 1))
    return {"matrix": matrix}


@router.get("/rq/{rq_id}")
def insights_by_rq(rq_id: str) -> dict[str, Any]:
    items = _filter_insights(_load_insights(), rq=rq_id.upper())
    return {"rq_id": rq_id.upper(), "count": len(items), "items": items[:20]}


@router.get("/segments")
def segments() -> dict[str, Any]:
    insights = _load_insights()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for card in insights:
        for seg in card.get("segment_relevance", []) or ["general"]:
            grouped.setdefault(seg, []).append(
                {
                    "insight_id": card.get("insight_id"),
                    "statement": card.get("statement"),
                    "confidence_tier": card.get("confidence_tier"),
                    "evidence_count": card.get("evidence_count"),
                }
            )
    return {"segments": grouped}


@router.get("/validation")
def validation_metrics() -> dict[str, Any]:
    validation = load_json(validation_path())
    summary = load_json(summary_path())
    run = validation.get("validation_run", {}) if isinstance(validation, dict) else {}
    synth = summary.get("validation", {}) if isinstance(summary, dict) else {}
    return {
        "run_id": run.get("run_id"),
        "pipeline_run_id": run.get("pipeline_run_id"),
        "agreement_rate": run.get("agreement_rate", synth.get("agreement_rate")),
        "barrier_agreement": run.get("barrier_agreement", synth.get("barrier_agreement")),
        "funnel_agreement": run.get("funnel_agreement", synth.get("funnel_agreement")),
        "competitor_agreement": run.get("competitor_agreement", synth.get("competitor_agreement")),
        "sample_size": run.get("sample_size", synth.get("sample_size")),
        "confidence_tiers": summary.get("synthesis", {}).get("confidence_tiers", {})
        if isinstance(summary, dict)
        else {},
    }
