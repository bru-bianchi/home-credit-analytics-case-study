"""CLI entrypoint for silver-to-gold SQL transformations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from credit_risk_pipeline.gold import build_gold_layer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build gold tables from versioned SQL scripts and export them to parquet."
    )
    parser.add_argument(
        "--table",
        action="append",
        dest="tables",
        help="Optional gold table_name to process. Can be passed multiple times.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_gold_layer(selected_tables=args.tables)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
