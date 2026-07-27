"""Export random insight sample for human audit (Phase 4)."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Export audit sample CSV")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    print(f"Audit export not yet implemented. run_id={args.run_id}, count={args.count}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
