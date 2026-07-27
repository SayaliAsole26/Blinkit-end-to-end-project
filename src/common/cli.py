"""CLI entry point — extended in Phase 1+."""

from __future__ import annotations

import typer
from dotenv import load_dotenv

from common.config import ensure_data_directories, load_settings
from common.logging import setup_logging
from common.run_id import generate_run_id

load_dotenv()

app = typer.Typer(
    name="blinkit",
    help="Blinkit Review Analyzer Dashboard — ingest, analyze, and view review insights",
    no_args_is_help=True,
)


@app.command("init")
def init_project() -> None:
    """Initialize data directories and verify configuration."""
    settings = load_settings()
    setup_logging(settings.logging.level, settings.logging.format)
    ensure_data_directories(settings)
    run_id = generate_run_id("init")
    typer.echo(f"Project initialized. Run ID: {run_id}")
    typer.echo(f"Taxonomy version: {settings.taxonomy_version}")


if __name__ == "__main__":
    app()
