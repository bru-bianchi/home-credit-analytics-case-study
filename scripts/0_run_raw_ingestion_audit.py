"""CLI entrypoint for raw layer validation and metadata persistence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from credit_risk_analytics.ingestion.raw_files_validator import (
    build_ingestion_report,
    write_report,
)
from credit_risk_analytics.ingestion.metadata_store import (
    load_cached_validation_results,
    persist_raw_validation_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate raw CSV files and persist raw validation metadata in DuckDB."
    )
    parser.add_argument(
        "--raw-dir",
        default=str(PROJECT_ROOT / "data" / "raw"),
        help="Directory containing the raw CSV files.",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "artifacts" / "ingestion" / "raw_ingestion_report.json"),
        help="Path to the JSON audit report generated from the raw files.",
    )
    parser.add_argument(
        "--database",
        default=str(PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"),
        help="Path to the local DuckDB database file used to store validation metadata.",
    )
    parser.add_argument(
        "--warehouse-output",
        default=str(PROJECT_ROOT / "artifacts" / "ingestion" / "duckdb_load_report.json"),
        help="Path to the JSON report generated from the DuckDB metadata persistence step.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_dir = Path(args.raw_dir).resolve()
    output_path = Path(args.output).resolve()
    database_path = Path(args.database).resolve()
    warehouse_output_path = Path(args.warehouse_output).resolve()

    cached_validations = load_cached_validation_results(raw_dir, database_path)
    report = build_ingestion_report(raw_dir, cached_validations=cached_validations)
    write_report(report, output_path)
    warehouse_report = persist_raw_validation_report(raw_dir, database_path, report)
    warehouse_output_path.parent.mkdir(parents=True, exist_ok=True)
    warehouse_output_path.write_text(
        json.dumps(warehouse_report, indent=2), encoding="utf-8"
    )

    print(json.dumps(report, indent=2))
    has_invalid_or_missing_files = (
        report["table_count_validation_failed"] > 0 or report["table_count_missing"] > 0
    )
    return 0 if not has_invalid_or_missing_files else 1


if __name__ == "__main__":
    raise SystemExit(main())
