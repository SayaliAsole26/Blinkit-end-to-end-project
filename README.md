# Blinkit Review Analyzer Dashboard

AI-powered review analyzer dashboard for Blinkit. Ingests public feedback from app stores, social, and forums; runs a batch NLP pipeline; and surfaces validated cross-category shopping insights — not raw sentiment.

## Documentation

- **[Final Discovery Engine Report](Docs/final-discovery-engine-report.md)** — presentation draft (RQ1–RQ8 answers + methodology)
- **[Executive Deck](Docs/executive-deck.md)** — 10-slide summary for stakeholders
- [Problem Statement](Docs/Problemstatement.md)
- [Architecture](Docs/architecture.md)
- [Implementation Plan](Docs/implementation-plan.md)
- [Deployment Playbook](Docs/deployment-playbook.md) — operational runbook
- [Deployment Plan](Docs/deployment-plan.md) — overview
  - [Backend — Railway](Docs/deployment-plan-backend-railway.md)
  - [Frontend — Vercel](Docs/deployment-plan-frontend-vercel.md) (Stitch HTML export)
- [Edge Cases](Docs/edge-case.md)

## Phase 0 Setup

### Prerequisites

- Python 3.11+
- pip

### Install

```bash
# Windows (PowerShell)
py -m pip install -e ".[dev]"

# Or with Makefile (Git Bash / WSL)
make install-dev
```

### Initialize project

```bash
py -m common.cli init
# or: blinkit init
```

### Configure secrets

```bash
copy .env.example .env
# Edit .env and set GROQ_API_KEY (required from Phase 3)
```

### Run tests

```bash
py -m pytest tests/ -v
# or: make test
```

## Project Structure

```
config/           # YAML settings, taxonomy, vocabulary
src/
  common/         # run_id, logging, config loader, CLI
  ingestion/      # Phase 1 — source connectors
  pipeline/       # Phase 2+ — processing stages
  models/         # Pydantic schemas
  storage/        # metadata DB, vector store, cache
  api/            # Phase 5 — FastAPI
data/             # raw, processed, insights (gitignored contents)
dashboard/        # Phase 5 — Streamlit
scripts/          # pipeline runner, audit export
tests/
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Install package |
| `make install-dev` | Install with dev dependencies |
| `make test` | Run pytest |
| `make lint` | Run ruff |
| `make ingest` | Pipeline ingest help (Phase 1) |
| `make pipeline` | Full pipeline help (Phase 4) |
| `make dashboard` | Dashboard help (API + frontend + Streamlit targets) |
| `make dashboard-api` | Start FastAPI on :8000 |
| `make dashboard-frontend` | Start Vercel-style static frontend on :3000 |
| `make dashboard-streamlit` | Start local Streamlit prototype |

## Current Status

**Project complete** — all phases (0–6) implemented per [implementation-plan.md](Docs/implementation-plan.md).

| Phase | Status |
|-------|--------|
| 0 Setup | Config, logging, Makefile, data dirs |
| 1 Ingestion | 5 connectors, 1,200-record sample corpus, raw store |
| 2 Clean & Embed | Filter → preprocess → clean → BGE-small + ChromaDB |
| 3 Cluster & Label | Dual-track HDBSCAN, Groq (1×/cluster), search-gap TF-IDF |
| 4 Synthesis & Validate | 117 insight cards, 10% Groq agreement, human audit export |
| 5 Dashboard | FastAPI + 9 Stitch views (all API-wired), Streamlit local |
| 6 Deployment | Docker, Railway, Vercel, GitHub Actions CI |

**Tests:** 106 pytest · `ruff check src tests` clean

**Phase 1 complete** — ingestion across 5 platforms (Play Store, App Store, Reddit, Twitter, Forum).

**Phase 2 complete** — filter → preprocess → clean → embed (`clean_embed` stage):
- Exact dedup, bot/spam filter, template-family tagging, review-bomb flag
- Record-aware segmentation (<280 chars → single segment)
- Category/competitor enrichment, logistics + search-gap tags, `embed_text` for BGE
- BGE-small embeddings in ChromaDB with SHA-256 cache

**Phase 2–3 design updated** — data-driven pipeline tuning in [architecture.md](Docs/architecture.md) and [implementation-plan.md](Docs/implementation-plan.md):
- Record-aware preprocessing (<280 chars → single segment)
- Embed enrichment (`embed_text` with category/competitor prefix)
- Dual-track parallel clustering (discovery + search-gap)
- HDBSCAN `min_cluster_size=3`, dedup merge at 0.90

### Quick start — ingest + clean/embed

```bash
python scripts/generate_sample_corpus.py   # 1200 records, 5 platforms
python -m pipeline ingest --source all
python -m pipeline run --stage clean_embed --run-id run_001
# Or:
python scripts/run_pipeline.py --run-id run_001 --stage clean_embed
```

Outputs:
- `data/processed/filter_audit_<run_id>.json`
- `data/processed/segments/segments_<run_id>.jsonl`
- `data/processed/clean_embed_summary_<run_id>.json`
- `data/processed/chroma/` (segment vectors)
- `data/processed/embedding_cache.db`

**Phase 4 complete** — synthesis, validation, and insight cards in `data/insights/`.

**Phase 5 complete** — FastAPI backend + 9 dashboard views (Overview, Insight Explorer, Barrier Chart, Funnel, Competitors, RQ Map, Segments, Evidence, Validation). All views wired to live API; no sentiment % in UI.

**Phase 6 complete** — Railway API + Vercel frontend deploy scripts; GitHub Actions CI (`pytest` + `ruff`).

## Deployment (Stitch UI + Railway API)

| Layer | Platform | Guide |
|-------|----------|-------|
| **Playbook** | Railway + Vercel | [deployment-playbook.md](Docs/deployment-playbook.md) |
| Overview | — | [deployment-plan.md](Docs/deployment-plan.md) |
| Backend API | Railway | [deployment-plan-backend-railway.md](Docs/deployment-plan-backend-railway.md) |
| Frontend (Stitch HTML) | Vercel | [deployment-plan-frontend-vercel.md](Docs/deployment-plan-frontend-vercel.md) |

**Production:** [Dashboard](https://blinkit-end-to-end-project.vercel.app) · [API](https://blinkit-end-to-end-project-production.up.railway.app)

**Stitch source:** `stitch_blinkit_review_analyzer_dashboard.zip` → `stitch/`  
**Deployable frontend:** `frontend/public/` · **All 9 views API-wired**

**Deploy order:** Railway API → update `frontend/vercel.json` proxy URL → Vercel deploy.

```powershell
.\scripts\deploy_railway.ps1    # backend
.\scripts\deploy_vercel.ps1      # frontend
```

```powershell
# Local API
$env:PYTHONPATH="src"; $env:BLINKIT_DATA_DIR="data"; $env:INSIGHTS_RUN_ID="run_phase4_final"
$env:CORS_ORIGINS="http://localhost:3000"
uvicorn api.main:app --reload --port 8000

# Local frontend
cd frontend && npm install && npm run dev
```
