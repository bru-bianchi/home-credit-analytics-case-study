"""CLI entrypoint for raw-to-bronze transformation and warehouse ingestion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from credit_risk_analysis.bronze import build_bronze_layer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build bronze parquet files from raw CSVs and ingest them into DuckDB."
    )
    parser.add_argument(
        "--table",
        action="append",
        dest="tables",
        help="Optional raw table_name to process. Can be passed multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only generate the transformation plan report, without writing parquet or loading the warehouse.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_bronze_layer(selected_tables=args.tables, dry_run=args.dry_run)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
