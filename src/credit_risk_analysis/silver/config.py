"""Shared configuration for the silver transformation process."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SILVER_SQL_DIR = PROJECT_ROOT / "sql" / "silver"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "silver"
SILVER_TRANSFORMATION_VERSION = "silver_transformation_v2"
