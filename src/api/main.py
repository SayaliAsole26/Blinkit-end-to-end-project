"""FastAPI application — read-only dashboard API for Railway."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.insights import router as insights_router

app = FastAPI(
    title="Blinkit Review Analyzer API",
    description="Read-only API serving validated cross-shopping insight cards.",
    version="0.1.0",
    docs_url="/docs" if os.environ.get("ENABLE_OPENAPI", "false").lower() == "true" else None,
    redoc_url=None,
)

origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(insights_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
