"""Stages 5–7 + 9 — Groq labeler: one merged call per discovery cluster."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from common.config import AppSettings, load_settings, load_taxonomy, resolve_path
from common.logging import get_logger, log_event
from models.friction import ClusterAnalysis, CrossShoppingFrictionAnalysis
from pipeline.cluster import DiscoveryCluster

logger = get_logger(__name__)

UNLABELED_BARRIER = "AWARENESS_DEFICIT"
UNLABELED_FUNNEL = "DISCOVERY"


class GroqClientProtocol(Protocol):
    def chat_completion(self, prompt: str) -> tuple[str, int]: ...


@dataclass
class GroqCallRecord:
    cluster_id: str
    cluster_hash: str
    tokens_used: int = 0
    status: str = "success"
    from_cache: bool = False


@dataclass
class LabelResult:
    analyses: list[ClusterAnalysis]
    unlabeled_cluster_ids: list[str] = field(default_factory=list)
    call_records: list[GroqCallRecord] = field(default_factory=list)
    total_tokens: int = 0
    api_call_count: int = 0
    cache_hits: int = 0

    def summary(self) -> dict:
        return {
            "labeled_count": len(self.analyses),
            "unlabeled_count": len(self.unlabeled_cluster_ids),
            "api_call_count": self.api_call_count,
            "cache_hits": self.cache_hits,
            "total_tokens": self.total_tokens,
        }


def _truncate(text: str, max_chars: int = 300) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def build_cluster_prompt(cluster: DiscoveryCluster, taxonomy_version: str) -> str:
    """Build merged prompt for friction + theme + RQ tagging."""
    taxonomy = load_taxonomy()
    barriers = ", ".join(b.id for b in taxonomy.cognitive_barriers)
    funnel_stages = ", ".join(s.id for s in taxonomy.funnel_leak_stages)
    advantages = ", ".join(a.id for a in taxonomy.competitor_advantages)
    rqs = ", ".join(r.id for r in taxonomy.research_questions)

    rep_lines = []
    for i, seg in enumerate(cluster.representatives, 1):
        rep_lines.append(
            f"{i}. [{seg.platform}] { _truncate(seg.normalized_text or seg.text)}"
        )

    cat_dist = json.dumps(cluster.category_distribution)
    plat_dist = json.dumps(cluster.platform_distribution)
    competitors = ", ".join(cluster.competitor_mentions) or "none detected"

    return f"""You analyze Blinkit app review clusters about cross-category shopping friction.

Taxonomy version: {taxonomy_version}

Representative segments ({len(cluster.representatives)}):
{chr(10).join(rep_lines)}

Category mention distribution: {cat_dist}
Platform distribution: {plat_dist}
Pre-detected competitor mentions: {competitors}
Cluster member count: {len(cluster.segment_ids)}

Classify this cluster with ONE JSON object matching this schema:
{{
  "cluster_id": "{cluster.cluster_id}",
  "friction": {{
    "user_cognitive_barrier": "<one of: {barriers}>",
    "funnel_leak_stage": "<one of: {funnel_stages}>",
    "competitor_entity": "<string or null>",
    "competitor_advantage": "<one of: {advantages} or null>",
    "price_sensitivity_detected": <boolean>
  }},
  "theme_label": "<short human-readable theme, 5-12 words>",
  "related_RQs": ["<one or more of: {rqs}>"],
  "segment_relevance": ["<optional audience segments, e.g. pet_owners, first_time_buyers>"],
  "taxonomy_version": "{taxonomy_version}"
}}

Rules:
- Assign exactly ONE primary cognitive barrier.
- Map to at least one research question (RQ1-RQ8).
- Use ASSORTMENT_GAP only when search/inventory void is the primary issue.
- Return valid JSON only, no markdown."""


def _default_unlabeled(cluster_id: str, taxonomy_version: str) -> ClusterAnalysis:
    return ClusterAnalysis(
        cluster_id=cluster_id,
        friction=CrossShoppingFrictionAnalysis(
            user_cognitive_barrier=UNLABELED_BARRIER,
            funnel_leak_stage=UNLABELED_FUNNEL,
            competitor_entity=None,
            competitor_advantage=None,
            price_sensitivity_detected=False,
        ),
        theme_label="UNLABELED",
        related_RQs=["RQ6"],
        segment_relevance=[],
        taxonomy_version=taxonomy_version,
    )


class LabelCache:
    """Skip re-label when cluster hash + taxonomy unchanged."""

    def __init__(self, path: Path | None = None) -> None:
        settings = load_settings()
        self.path = path or resolve_path(
            f"{settings.paths.processed_data}/label_cache.json"
        )
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, cluster_hash: str, taxonomy_version: str) -> ClusterAnalysis | None:
        entry = self._data.get(cluster_hash)
        if entry and entry.get("taxonomy_version") == taxonomy_version:
            try:
                return ClusterAnalysis.model_validate(entry["analysis"])
            except ValidationError:
                return None
        return None

    def put(self, cluster_hash: str, analysis: ClusterAnalysis) -> None:
        self._data[cluster_hash] = {
            "taxonomy_version": analysis.taxonomy_version,
            "analysis": analysis.model_dump(mode="json"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


class GroqClient:
    """Production Groq API client."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set")
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = self.settings.groq.model
        self._temperature = self.settings.groq.temperature
        self._max_tokens = self.settings.groq.max_tokens

    def chat_completion(self, prompt: str) -> tuple[str, int]:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content or "{}"
        tokens = response.usage.total_tokens if response.usage else 0
        return content, tokens


class MockGroqClient:
    """Deterministic mock for tests — returns valid ClusterAnalysis JSON."""

    call_count: int = 0
    tokens_per_call: int = 100

    def chat_completion(self, prompt: str) -> tuple[str, int]:
        MockGroqClient.call_count += 1
        cluster_id = "disc_0000"
        if '"cluster_id": "' in prompt:
            start = prompt.index('"cluster_id": "') + len('"cluster_id": "')
            end = prompt.index('"', start)
            cluster_id = prompt[start:end]

        payload = {
            "cluster_id": cluster_id,
            "friction": {
                "user_cognitive_barrier": "AWARENESS_DEFICIT",
                "funnel_leak_stage": "DISCOVERY",
                "competitor_entity": None,
                "competitor_advantage": None,
                "price_sensitivity_detected": False,
            },
            "theme_label": "Unaware of non-grocery categories on Blinkit",
            "related_RQs": ["RQ2", "RQ3"],
            "segment_relevance": ["grocery_loyalists"],
            "taxonomy_version": "1.0.0",
        }
        return json.dumps(payload), self.tokens_per_call


class GroqLabeler:
    """Label discovery clusters — exactly one Groq call per cluster."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        client: GroqClientProtocol | None = None,
        cache: LabelCache | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.client = client
        self.cache = cache or LabelCache()
        self.max_retries = self.settings.groq.max_retries

    def _parse_response(self, raw: str, cluster_id: str) -> ClusterAnalysis:
        data = json.loads(raw)
        if "cluster_id" not in data:
            data["cluster_id"] = cluster_id
        return ClusterAnalysis.model_validate(data)

    def label_cluster(self, cluster: DiscoveryCluster) -> tuple[ClusterAnalysis, GroqCallRecord]:
        """One merged Groq call for friction + theme + RQs."""
        taxonomy_version = self.settings.taxonomy_version
        cluster.compute_hash(taxonomy_version)

        cached = self.cache.get(cluster.cluster_hash, taxonomy_version)
        if cached:
            record = GroqCallRecord(
                cluster_id=cluster.cluster_id,
                cluster_hash=cluster.cluster_hash,
                status="cached",
                from_cache=True,
            )
            return cached, record

        if self.client is None:
            raise RuntimeError("Groq client not configured")

        prompt = build_cluster_prompt(cluster, taxonomy_version)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                raw, tokens = self.client.chat_completion(prompt)
                analysis = self._parse_response(raw, cluster.cluster_id)
                self.cache.put(cluster.cluster_hash, analysis)
                record = GroqCallRecord(
                    cluster_id=cluster.cluster_id,
                    cluster_hash=cluster.cluster_hash,
                    tokens_used=tokens,
                    status="success",
                )
                return analysis, record
            except (json.JSONDecodeError, ValidationError, KeyError) as exc:
                last_error = exc
                logger.warning(
                    "Groq parse failure for %s (attempt %d): %s",
                    cluster.cluster_id,
                    attempt + 1,
                    exc,
                )

        logger.error("Cluster %s marked UNLABELED after retries", cluster.cluster_id)
        analysis = _default_unlabeled(cluster.cluster_id, taxonomy_version)
        record = GroqCallRecord(
            cluster_id=cluster.cluster_id,
            cluster_hash=cluster.cluster_hash,
            status="unlabeled",
        )
        if last_error:
            logger.debug("Last error: %s", last_error)
        return analysis, record

    def label_clusters(
        self,
        clusters: list[DiscoveryCluster],
        *,
        run_id: str | None = None,
    ) -> LabelResult:
        """Label all discovery clusters with budget guardrail."""
        result = LabelResult(analyses=[])
        n_clusters = len(clusters)

        for cluster in clusters:
            if not cluster.segment_ids:
                continue

            analysis, record = self.label_cluster(cluster)
            result.analyses.append(analysis)
            result.call_records.append(record)

            if record.from_cache:
                result.cache_hits += 1
            elif record.status == "success":
                result.api_call_count += 1
                result.total_tokens += record.tokens_used
            elif record.status == "unlabeled":
                result.unlabeled_cluster_ids.append(cluster.cluster_id)

        max_calls = int(n_clusters * 1.2)
        if result.api_call_count > max_calls:
            log_event(
                logger,
                logging.WARNING,
                f"Groq call count {result.api_call_count} exceeds guardrail {max_calls}",
                run_id=run_id,
                stage="groq_label",
                counts={"api_calls": result.api_call_count, "clusters": n_clusters},
            )

        return result
