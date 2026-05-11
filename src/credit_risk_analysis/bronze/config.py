"""Shared configuration for the bronze transformation process."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "bronze"
BRONZE_COLUMN_MAPPING_PATH = PROJECT_ROOT / "docs" / "references" / "bronze_column_mapping.csv"
BRONZE_SCHEMA_MAPPING_PATH = PROJECT_ROOT / "docs" / "references" / "bronze_schema_mapping.csv"
BRONZE_SENTINEL_MAPPING_PATH = PROJECT_ROOT / "docs" / "references" / "bronze_sentinel_mapping.csv"

BOOLEAN_LITERALS = {"0", "1", "true", "false", "y", "n", "yes", "no"}
BRONZE_TRANSFORMATION_VERSION = "bronze_transformation_v1"
