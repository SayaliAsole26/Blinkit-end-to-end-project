"""Validate YAML configuration files against Pydantic schemas."""

from pathlib import Path

import pytest
import yaml

from common.config import (
    CONFIG_DIR,
    CategoryVocabularyConfig,
    CompetitorAliasesConfig,
    TaxonomyConfig,
    load_category_vocabulary,
    load_competitor_aliases,
    load_settings,
    load_taxonomy,
)


@pytest.fixture
def config_dir() -> Path:
    return CONFIG_DIR


def test_settings_yaml_valid(config_dir: Path) -> None:
    settings = load_settings(config_dir)
    assert settings.taxonomy_version == "1.0.0"
    assert settings.embedding.model == "BAAI/bge-small-en-v1.5"
    assert settings.embedding.batch_size >= 1
    assert settings.clustering.min_cluster_size == 3
    assert settings.clustering.dedup_threshold == 0.90
    assert settings.preprocess.short_record_char_threshold == 280
    assert settings.clean.embed_enrichment is True


def test_taxonomy_yaml_valid(config_dir: Path) -> None:
    taxonomy = load_taxonomy(config_dir)
    assert taxonomy.version == "1.0.0"
    barrier_ids = {b.id for b in taxonomy.cognitive_barriers}
    assert "AWARENESS_DEFICIT" in barrier_ids
    assert "NONE_GROCERY_LOYAL" in barrier_ids
    assert len(taxonomy.funnel_leak_stages) == 4
    assert len(taxonomy.research_questions) == 8


def test_category_vocabulary_yaml_valid(config_dir: Path) -> None:
    vocab = load_category_vocabulary(config_dir)
    assert vocab.version == "1.0.0"
    assert len(vocab.mappings) >= 5
    assert "pet_supplies" in {m.category_id for m in vocab.mappings}
    assert len(vocab.logistics_keywords) >= 3


def test_competitor_aliases_yaml_valid(config_dir: Path) -> None:
    competitors = load_competitor_aliases(config_dir)
    canonical = {c.canonical for c in competitors.competitors}
    assert "Amazon" in canonical
    assert "Zepto" in canonical
    assert "Instamart" in canonical


def test_taxonomy_barrier_ids_unique(config_dir: Path) -> None:
    data = yaml.safe_load((config_dir / "taxonomy_v1.yaml").read_text(encoding="utf-8"))
    taxonomy = TaxonomyConfig.model_validate(data)
    ids = [b.id for b in taxonomy.cognitive_barriers]
    assert len(ids) == len(set(ids))


def test_competitor_aliases_non_empty(config_dir: Path) -> None:
    config = load_competitor_aliases(config_dir)
    for entry in config.competitors:
        assert entry.canonical
        assert len(entry.aliases) >= 1
