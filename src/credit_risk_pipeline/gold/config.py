"""Shared configuration for the gold transformation process."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLD_SQL_DIR = PROJECT_ROOT / "sql" / "gold"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "gold"
GOLD_TRANSFORMATION_VERSION = "gold_transformation_v1"
