"""Full pipeline orchestrator."""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Blinkit review analyzer pipeline")
    parser.add_argument("--run-id", required=True, help="Pipeline run identifier")
    parser.add_argument(
        "--stage",
        default="all",
        help="Stage to run: all, clean_embed, cluster_label, synthesize_validate",
    )
    parser.add_argument(
        "--ingestion-run-id",
        default=None,
        help="Optional ingestion run to process (default: all raw records)",
    )
    parser.add_argument(
        "--segments-run-id",
        default=None,
        help="clean_embed run ID for cluster_label (default: same as --run-id)",
    )
    parser.add_argument(
        "--skip-groq",
        action="store_true",
        help="Skip Groq labeling in cluster_label stage",
    )
    args = parser.parse_args()

    if args.stage in ("all", "clean_embed"):
        from pipeline.clean_embed import CleanEmbedPipeline

        result = CleanEmbedPipeline().run(
            pipeline_run_id=args.run_id,
            ingestion_run_id=args.ingestion_run_id,
        )
        print(json.dumps(result.to_dict(), indent=2))
        if args.stage == "clean_embed":
            return 0 if result.total_input_records > 0 else 1

    if args.stage in ("all", "cluster_label"):
        from pipeline.cluster_label import ClusterLabelPipeline

        result = ClusterLabelPipeline().run(
            pipeline_run_id=args.run_id,
            segments_run_id=args.segments_run_id or args.run_id,
            skip_groq=args.skip_groq,
        )
        print(json.dumps(result.to_dict(), indent=2))
        if args.stage == "cluster_label":
            return 0 if result.total_segments > 0 else 1

    if args.stage == "all":
        print("Stages after cluster_label not yet implemented.")
        return 1

    print(f"Stage '{args.stage}' not yet implemented.")
    return 1


if __name__ == "__main__":
    sys.exit(main())