"""Load and validate YAML configuration files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class EmbeddingSettings(BaseModel):
    model: str
    batch_size: int = Field(ge=1)
    dimensions: int = Field(ge=1)
    cache_path: str
    instruction_prefix: str = ""


class ClusteringSettings(BaseModel):
    algorithm: Literal["hdbscan", "kmeans"]
    min_cluster_size: int = Field(ge=2)
    metric: str
    dedup_threshold: float = Field(ge=0.0, le=1.0)
    kmeans_fallback_k: int = Field(ge=2)
    noise_threshold_pct: float = Field(ge=0.0, le=1.0)
    dual_track: bool = True


class GroqSettings(BaseModel):
    model: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(ge=1)
    max_retries: int = Field(ge=0)


class PreprocessSettings(BaseModel):
    sentence_splitter: str
    short_record_char_threshold: int = Field(ge=0)
    min_segment_chars: int = Field(ge=1)
    max_snippets_per_cluster: int = Field(ge=1)
    max_snippet_tokens: int = Field(ge=1)


class FilterSettings(BaseModel):
    review_bomb_window_hours: int = Field(ge=1)
    review_bomb_threshold: int = Field(ge=1)
    near_duplicate_jaccard_threshold: float = Field(ge=0.0, le=1.0)
    tag_template_families: bool = True


class CleanSettings(BaseModel):
    embed_enrichment: bool = True
    hinglish_devanagari_exclude_threshold: float = Field(ge=0.0, le=1.0)
    strip_handles_for_embed: bool = True


class ValidationSettings(BaseModel):
    resample_rate: float = Field(ge=0.0, le=1.0)
    agreement_target: float = Field(ge=0.0, le=1.0)
    stale_months: int = Field(ge=1)


class CorpusProfileSettings(BaseModel):
    typical_record_count: int = Field(ge=1)
    expected_segments_min: int = Field(ge=1)
    expected_segments_max: int = Field(ge=1)
    expected_discovery_clusters: str = ""
    expected_search_gap_clusters: str = ""
    expected_groq_calls: str = ""


class PathsSettings(BaseModel):
    config_dir: str
    raw_data: str
    processed_data: str
    insights: str
    metadata_db: str
    logs: str


class LoggingSettings(BaseModel):
    level: str
    format: Literal["json", "text"]


class AppSettings(BaseModel):
    taxonomy_version: str
    embedding: EmbeddingSettings
    clustering: ClusteringSettings
    groq: GroqSettings
    preprocess: PreprocessSettings
    filter: FilterSettings
    clean: CleanSettings
    validation: ValidationSettings
    corpus_profile: CorpusProfileSettings | None = None
    paths: PathsSettings
    logging: LoggingSettings


class TaxonomyItem(BaseModel):
    id: str
    label: str | None = None
    description: str | None = None
    question: str | None = None
    min_platforms: int | None = None
    min_agreement: float | None = None


class TaxonomyConfig(BaseModel):
    version: str
    name: str
    cognitive_barriers: list[TaxonomyItem]
    funnel_leak_stages: list[TaxonomyItem]
    competitor_advantages: list[TaxonomyItem]
    research_questions: list[TaxonomyItem]
    confidence_tiers: list[TaxonomyItem]


class CategoryMapping(BaseModel):
    phrases: list[str]
    category_id: str


class CategoryVocabularyConfig(BaseModel):
    version: str
    mappings: list[CategoryMapping]
    fuzzy_match_threshold: int = Field(ge=0, le=100)
    logistics_keywords: list[str]
    search_gap_patterns: list[str]


class CompetitorEntry(BaseModel):
    canonical: str
    aliases: list[str]
    default_advantages: list[str] = Field(default_factory=list)
    note: str | None = None


class CompetitorAliasesConfig(BaseModel):
    version: str
    competitors: list[CompetitorEntry]
    comparison_phrases: list[str]


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def load_settings(config_dir: Path | None = None) -> AppSettings:
    root = config_dir or CONFIG_DIR
    data = _load_yaml(root / "settings.yaml")
    return AppSettings.model_validate(data)


@lru_cache
def load_taxonomy(config_dir: Path | None = None) -> TaxonomyConfig:
    root = config_dir or CONFIG_DIR
    data = _load_yaml(root / "taxonomy_v1.yaml")
    return TaxonomyConfig.model_validate(data)


@lru_cache
def load_category_vocabulary(config_dir: Path | None = None) -> CategoryVocabularyConfig:
    root = config_dir or CONFIG_DIR
    data = _load_yaml(root / "category_vocabulary.yaml")
    return CategoryVocabularyConfig.model_validate(data)


@lru_cache
def load_competitor_aliases(config_dir: Path | None = None) -> CompetitorAliasesConfig:
    root = config_dir or CONFIG_DIR
    data = _load_yaml(root / "competitor_aliases.yaml")
    return CompetitorAliasesConfig.model_validate(data)


def resolve_path(relative: str) -> Path:
    """Resolve a config path relative to project root."""
    path = PROJECT_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_data_directories(settings: AppSettings | None = None) -> None:
    """Create data, log, and config output directories."""
    settings = settings or load_settings()
    for rel in (
        settings.paths.raw_data,
        settings.paths.processed_data,
        f"{settings.paths.processed_data}/segments",
        f"{settings.paths.processed_data}/chroma",
        settings.paths.insights,
        settings.paths.logs,
    ):
        resolve_path(rel).mkdir(parents=True, exist_ok=True)
