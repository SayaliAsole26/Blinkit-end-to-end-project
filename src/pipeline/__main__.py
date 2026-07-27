"""Pipeline CLI — ingest and run stages."""

from __future__ import annotations

import json

import typer
from dotenv import load_dotenv

from common.config import ensure_data_directories, load_settings
from common.logging import setup_logging
from common.run_id import generate_run_id
from ingestion.service import IngestionService
from pipeline.clean_embed import CleanEmbedPipeline
from pipeline.cluster_label import ClusterLabelPipeline

load_dotenv()

app = typer.Typer(
    name="pipeline",
    help="Blinkit Review Analyzer Dashboard — pipeline commands",
    no_args_is_help=True,
)


@app.command("ingest")
def ingest(
    source: str = typer.Option(
        "all",
        help="Source: play_store, app_store, reddit, twitter, forum, all",
    ),
    run_id: str | None = typer.Option(None, help="Ingestion run ID (auto-generated if omitted)"),
) -> None:
    """Ingest feedback from external sources into the immutable raw store."""
    settings = load_settings()
    setup_logging(settings.logging.level, settings.logging.format)
    ensure_data_directories(settings)

    effective_run_id = run_id or generate_run_id("ingest")
    service = IngestionService()
    summary = service.ingest(source=source, run_id=effective_run_id)

    typer.echo(json.dumps(summary.to_dict(), indent=2))
    if summary.total_in_store == 0:
        typer.echo(
            "Warning: no records ingested. Run scripts/generate_sample_corpus.py first.",
            err=True,
        )
        raise typer.Exit(code=1)
    typer.echo(f"\nIngestion complete: {summary.total_in_store} records in raw store.")


@app.command("run")
def run_stage(
    stage: str = typer.Option(..., help="Pipeline stage: clean_embed, cluster_label"),
    run_id: str | None = typer.Option(None, help="Pipeline run ID (auto-generated if omitted)"),
    ingestion_run_id: str | None = typer.Option(
        None,
        help="Limit to one ingestion run JSONL; default = all unique records in raw store",
    ),
    segments_run_id: str | None = typer.Option(
        None,
        help="clean_embed run ID for segments file (cluster_label; defaults to run_id)",
    ),
    skip_groq: bool = typer.Option(False, help="Skip Groq labeling (cluster_label only)"),
) -> None:
    """Run a pipeline stage."""
    settings = load_settings()
    setup_logging(settings.logging.level, settings.logging.format)
    ensure_data_directories(settings)

    effective_run_id = run_id or generate_run_id("pipeline")

    if stage == "clean_embed":
        pipeline = CleanEmbedPipeline(settings)
        result = pipeline.run(
            pipeline_run_id=effective_run_id,
            ingestion_run_id=ingestion_run_id,
        )
        typer.echo(json.dumps(result.to_dict(), indent=2))
        if result.total_input_records == 0:
            typer.echo("No records in raw store. Run ingest first.", err=True)
            raise typer.Exit(code=1)
        typer.echo(
            f"\nclean_embed complete: {result.embed_summary.get('embedded_count', 0)} "
            f"segments embedded (run_id={effective_run_id})."
        )
        return

    if stage == "cluster_label":
        pipeline = ClusterLabelPipeline(settings)
        result = pipeline.run(
            pipeline_run_id=effective_run_id,
            segments_run_id=segments_run_id,
            skip_groq=skip_groq,
        )
        typer.echo(json.dumps(result.to_dict(), indent=2))
        if result.total_segments == 0:
            typer.echo("No segments found. Run clean_embed first.", err=True)
            raise typer.Exit(code=1)
        typer.echo(
            f"\ncluster_label complete: {result.discovery.get('cluster_count', 0)} "
            f"discovery clusters, {result.search_gap.get('theme_count', 0)} search-gap themes "
            f"(run_id={effective_run_id})."
        )
        return

    typer.echo(f"Unknown stage '{stage}'. Supported: clean_embed, cluster_label", err=True)
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
