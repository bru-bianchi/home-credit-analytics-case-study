"""Load raw CSV files into a local DuckDB database."""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from credit_risk_analytics.ingestion.duckdb_loader import load_raw_tables_to_duckdb


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load validated raw CSV files into a local DuckDB database."
    )
    parser.add_argument(
        "--raw-dir",
        default=str(PROJECT_ROOT / "data" / "raw"),
        help="Directory containing the raw CSV files.",
    )
    parser.add_argument(
        "--database",
        default=str(PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"),
        help="Path to the local DuckDB database file.",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "artifacts" / "ingestion" / "duckdb_load_report.json"),
        help="Path to the JSON load report.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    raw_dir = Path(args.raw_dir).resolve()
    database_path = Path(args.database).resolve()
    output_path = Path(args.output).resolve()

    report = load_raw_tables_to_duckdb(raw_dir, database_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    has_successful_load = report["loaded_table_count"] > 0
    all_readable_were_already_processed = (
        report["ingestion_report"]["table_count_read_success"] > 0
        and report["loaded_table_count"] == 0
        and report["already_processed_table_count"]
        == report["ingestion_report"]["table_count_read_success"]
    )
    return 0 if has_successful_load or all_readable_were_already_processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
