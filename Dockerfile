# Blinkit Review Analyzer — multi-target Docker build
# Targets:
#   api      — slim FastAPI image for Railway (dashboard API) — MUST be final stage
#   pipeline — full ML stack for batch pipeline runs on Railway
#
# IMPORTANT: `api` is the last stage so Railway healthchecks pass even if
# dockerBuildTarget is not applied. The pipeline stage runs --help and exits.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BLINKIT_DATA_DIR=/app/data

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY config/ config/
COPY src/ src/
COPY scripts/ scripts/

# ---------------------------------------------------------------------------
# Pipeline — full dependency set for batch NLP jobs
# ---------------------------------------------------------------------------
FROM base AS pipeline

RUN pip install --upgrade pip && pip install -e .

CMD ["python", "scripts/run_pipeline.py", "--help"]

# ---------------------------------------------------------------------------
# API — lightweight FastAPI service (no sentence-transformers / chromadb)
# Default final stage for Railway when dockerBuildTarget is not applied.
# ---------------------------------------------------------------------------
FROM base AS api

ENV PYTHONPATH=/app/src

RUN pip install --upgrade pip && \
    pip install \
    pydantic pydantic-settings typer python-dotenv pyyaml \
    fastapi "uvicorn[standard]"

# Seed read-only insight data for Railway (avoids volume setup on first deploy)
COPY deploy/seed/insights/ /app/data/insights/
COPY deploy/seed/processed/ /app/data/processed/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health')" || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
