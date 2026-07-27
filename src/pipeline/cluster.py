"""Stage 5 — Discovery clustering (Track A): HDBSCAN, dedup merge, representatives."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from sklearn.cluster import KMeans

from common.config import AppSettings, load_settings
from common.logging import get_logger
from models.records import CleanSegment

logger = get_logger(__name__)

UNCLUSTERED = "UNCLUSTERED"


@dataclass
class DiscoveryCluster:
    """A discovery friction cluster ready for Groq labeling."""

    cluster_id: str
    segment_ids: list[str]
    centroid: np.ndarray
    representatives: list[CleanSegment] = field(default_factory=list)
    category_distribution: dict[str, int] = field(default_factory=dict)
    platform_distribution: dict[str, int] = field(default_factory=dict)
    competitor_mentions: list[str] = field(default_factory=list)
    cluster_hash: str = ""

    def compute_hash(self, taxonomy_version: str) -> str:
        payload = "|".join(sorted(self.segment_ids)) + f"|{taxonomy_version}"
        self.cluster_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self.cluster_hash


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _compute_centroid(vectors: np.ndarray) -> np.ndarray:
    centroid = vectors.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 1e-9:
        centroid = centroid / norm
    return centroid.astype(np.float32)


def _distribution_counts(segments: list[CleanSegment], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for seg in segments:
        if attr == "platform":
            key = seg.platform
        elif attr == "category":
            if seg.category_mentions:
                for cat in seg.category_mentions:
                    counts[cat] = counts.get(cat, 0) + 1
            continue
        else:
            key = getattr(seg, attr, "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _collect_competitors(segments: list[CleanSegment]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for seg in segments:
        for comp in seg.competitor_mentions_raw:
            if comp not in seen:
                seen.add(comp)
                result.append(comp)
    return result


def select_representatives(
    segments: list[CleanSegment],
    vectors: np.ndarray,
    *,
    min_count: int = 5,
    max_count: int = 10,
) -> list[CleanSegment]:
    """Pick diverse representative segments by platform/category spread."""
    if not segments:
        return []
    target = min(max_count, max(min_count, len(segments)))
    if len(segments) <= target:
        return list(segments)

    centroid = _compute_centroid(vectors)
    scored: list[tuple[float, int, CleanSegment]] = []
    for i, seg in enumerate(segments):
        sim = cosine_similarity(vectors[i], centroid)
        diversity = len(set(seg.category_mentions)) + (1 if seg.platform else 0)
        scored.append((sim, -diversity, seg))

    scored.sort(key=lambda x: (-x[0], x[1]))
    selected: list[CleanSegment] = [scored[0][2]]
    selected_platforms: set[str] = {scored[0][2].platform}
    selected_categories: set[str] = set(scored[0][2].category_mentions)

    for _, _, seg in scored[1:]:
        if len(selected) >= target:
            break
        is_diverse = (
            seg.platform not in selected_platforms
            or any(c not in selected_categories for c in seg.category_mentions)
        )
        if is_diverse or len(selected) < min_count:
            selected.append(seg)
            selected_platforms.add(seg.platform)
            selected_categories.update(seg.category_mentions)

    if len(selected) < min_count:
        for _, _, seg in scored:
            if seg not in selected:
                selected.append(seg)
            if len(selected) >= min_count:
                break

    return selected[:target]


def merge_similar_clusters(
    clusters: list[DiscoveryCluster],
    threshold: float,
) -> list[DiscoveryCluster]:
    """Merge clusters whose centroids exceed cosine similarity threshold."""
    if len(clusters) <= 1:
        return clusters

    parent = list(range(len(clusters)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            sim = cosine_similarity(clusters[i].centroid, clusters[j].centroid)
            if sim >= threshold:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(len(clusters)):
        root = find(i)
        groups.setdefault(root, []).append(i)

    merged: list[DiscoveryCluster] = []
    for indices in groups.values():
        if len(indices) == 1:
            merged.append(clusters[indices[0]])
            continue

        all_segment_ids: list[str] = []
        all_reps: list[CleanSegment] = []
        all_vectors: list[np.ndarray] = []
        merged_cats: dict[str, int] = {}
        merged_plats: dict[str, int] = {}
        merged_comps: list[str] = []
        seen_comps: set[str] = set()

        for idx in indices:
            c = clusters[idx]
            all_segment_ids.extend(c.segment_ids)
            all_reps.extend(c.representatives)
            all_vectors.append(c.centroid)
            for k, v in c.category_distribution.items():
                merged_cats[k] = merged_cats.get(k, 0) + v
            for k, v in c.platform_distribution.items():
                merged_plats[k] = merged_plats.get(k, 0) + v
            for comp in c.competitor_mentions:
                if comp not in seen_comps:
                    seen_comps.add(comp)
                    merged_comps.append(comp)

        unique_ids = list(dict.fromkeys(all_segment_ids))
        combined_centroid = _compute_centroid(np.stack(all_vectors))

        rep_map = {s.segment_id: s for s in all_reps}
        rep_segments: list[CleanSegment] = []
        seen_rep_ids: set[str] = set()
        for rep in all_reps:
            if rep.segment_id not in seen_rep_ids:
                seen_rep_ids.add(rep.segment_id)
                rep_segments.append(rep)

        merged_cluster = DiscoveryCluster(
            cluster_id=clusters[indices[0]].cluster_id,
            segment_ids=unique_ids,
            centroid=combined_centroid,
            representatives=rep_segments[:10],
            category_distribution=merged_cats,
            platform_distribution=merged_plats,
            competitor_mentions=merged_comps,
        )
        merged.append(merged_cluster)

    return merged


def assign_noise_to_nearest(
    noise_indices: list[int],
    vectors: np.ndarray,
    cluster_labels: np.ndarray,
    centroids: dict[int, np.ndarray],
    *,
    min_similarity: float = 0.5,
) -> np.ndarray:
    """Assign noise points to nearest cluster or mark UNCLUSTERED (-2)."""
    labels = cluster_labels.copy()
    for idx in noise_indices:
        best_label = -2
        best_sim = -1.0
        for label, centroid in centroids.items():
            sim = cosine_similarity(vectors[idx], centroid)
            if sim > best_sim:
                best_sim = sim
                best_label = label
        if best_sim >= min_similarity and best_label >= 0:
            labels[idx] = best_label
        else:
            labels[idx] = -2
    return labels


def run_hdbscan(
    vectors: np.ndarray,
    min_cluster_size: int,
    metric: str = "cosine",
) -> np.ndarray:
    import hdbscan

    work = vectors.astype(np.float32)
    effective_metric = metric
    if metric == "cosine":
        # Euclidean on L2-normalized vectors ≡ cosine distance (sklearn BallTree compat)
        norms = np.linalg.norm(work, axis=1, keepdims=True)
        work = work / np.maximum(norms, 1e-9)
        effective_metric = "euclidean"

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric=effective_metric,
        cluster_selection_method="eom",
    )
    return clusterer.fit_predict(work)


def run_kmeans_fallback(vectors: np.ndarray, k: int) -> np.ndarray:
    effective_k = min(k, len(vectors))
    if effective_k < 2:
        return np.zeros(len(vectors), dtype=int)
    km = KMeans(n_clusters=effective_k, random_state=42, n_init=10)
    return km.fit_predict(vectors)


@dataclass
class ClusterResult:
    clusters: list[DiscoveryCluster] = field(default_factory=list)
    noise_count: int = 0
    unclustered_count: int = 0
    algorithm_used: Literal["hdbscan", "kmeans_fallback"] = "hdbscan"
    input_count: int = 0

    def summary(self) -> dict:
        return {
            "cluster_count": len(self.clusters),
            "noise_count": self.noise_count,
            "unclustered_count": self.unclustered_count,
            "algorithm_used": self.algorithm_used,
            "input_count": self.input_count,
            "total_clustered_segments": sum(len(c.segment_ids) for c in self.clusters),
        }


class ClusterModule:
    """Track A — discovery friction clustering on non-logistics embeddings."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or load_settings()
        self.cluster_cfg = self.settings.clustering
        self.preprocess_cfg = self.settings.preprocess

    def run_discovery(
        self,
        segments: list[CleanSegment],
        embeddings: np.ndarray,
    ) -> ClusterResult:
        """Cluster non-logistics segments; dedup merge; select representatives."""
        if len(segments) != len(embeddings):
            raise ValueError("segments and embeddings length mismatch")

        eligible: list[CleanSegment] = []
        eligible_vectors: list[np.ndarray] = []
        for seg, vec in zip(segments, embeddings, strict=True):
            if seg.is_logistics_only or seg.embed_skipped:
                continue
            eligible.append(seg)
            eligible_vectors.append(vec)

        result = ClusterResult(input_count=len(eligible))
        if not eligible:
            return result

        vectors = np.stack(eligible_vectors, axis=0).astype(np.float32)
        labels = run_hdbscan(
            vectors,
            min_cluster_size=self.cluster_cfg.min_cluster_size,
            metric=self.cluster_cfg.metric,
        )

        noise_mask = labels == -1
        noise_pct = noise_mask.sum() / len(labels)
        result.noise_count = int(noise_mask.sum())

        if noise_pct > self.cluster_cfg.noise_threshold_pct:
            logger.info(
                "HDBSCAN noise %.1f%% exceeds threshold; using KMeans fallback k=%d",
                noise_pct * 100,
                self.cluster_cfg.kmeans_fallback_k,
            )
            labels = run_kmeans_fallback(vectors, self.cluster_cfg.kmeans_fallback_k)
            result.algorithm_used = "kmeans_fallback"
            result.noise_count = 0
        else:
            unique_labels = {int(l) for l in labels if l >= 0}
            centroids = {}
            for label in unique_labels:
                mask = labels == label
                centroids[label] = _compute_centroid(vectors[mask])

            noise_indices = [i for i, l in enumerate(labels) if l == -1]
            if noise_indices:
                labels = assign_noise_to_nearest(
                    noise_indices, vectors, labels, centroids
                )

        result.unclustered_count = int((labels == -2).sum())

        label_to_indices: dict[int, list[int]] = {}
        for i, label in enumerate(labels):
            if label < 0:
                continue
            label_to_indices.setdefault(int(label), []).append(i)

        raw_clusters: list[DiscoveryCluster] = []
        for label, indices in sorted(label_to_indices.items()):
            cluster_segments = [eligible[i] for i in indices]
            cluster_vectors = vectors[indices]
            cluster_id = f"disc_{label:04d}"

            cluster = DiscoveryCluster(
                cluster_id=cluster_id,
                segment_ids=[s.segment_id for s in cluster_segments],
                centroid=_compute_centroid(cluster_vectors),
                representatives=select_representatives(
                    cluster_segments,
                    cluster_vectors,
                    min_count=5,
                    max_count=self.preprocess_cfg.max_snippets_per_cluster,
                ),
                category_distribution=_distribution_counts(cluster_segments, "category"),
                platform_distribution=_distribution_counts(cluster_segments, "platform"),
                competitor_mentions=_collect_competitors(cluster_segments),
            )
            cluster.compute_hash(self.settings.taxonomy_version)
            raw_clusters.append(cluster)

        merged = merge_similar_clusters(
            raw_clusters,
            threshold=self.cluster_cfg.dedup_threshold,
        )

        seg_by_id = {s.segment_id: s for s in eligible}
        for i, cluster in enumerate(merged):
            if cluster.cluster_id.startswith("disc_"):
                cluster.cluster_id = f"disc_{i:04d}"
            cluster_segments = [seg_by_id[sid] for sid in cluster.segment_ids if sid in seg_by_id]
            if cluster_segments:
                cluster.category_distribution = _distribution_counts(cluster_segments, "category")
                cluster.platform_distribution = _distribution_counts(cluster_segments, "platform")
                cluster.competitor_mentions = _collect_competitors(cluster_segments)
                idxs = [
                    eligible.index(seg_by_id[sid])
                    for sid in cluster.segment_ids
                    if sid in seg_by_id
                ]
                cluster_vectors = vectors[idxs]
                cluster.representatives = select_representatives(
                    cluster_segments,
                    cluster_vectors,
                    min_count=5,
                    max_count=self.preprocess_cfg.max_snippets_per_cluster,
                )
            cluster.compute_hash(self.settings.taxonomy_version)

        result.clusters = merged
        return result
