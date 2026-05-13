"""Reference schema loading, validation, and column mapping for the bronze layer."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from credit_risk_pipeline.raw.config import RAW_TABLES
from utils.naming_utils import snake_case
from utils.duckdb_utils import quote_string

from .config import (
    BRONZE_COLUMN_MAPPING_PATH,
    BRONZE_SCHEMA_MAPPING_PATH,
    BRONZE_SENTINEL_MAPPING_PATH,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_SCHEMA_PATH = PROJECT_ROOT / "docs" / "references" / "HomeCredit_columns_description.csv"

REFERENCE_TABLE_MAPPING = {
    "application_{train|test}.csv": ["application_train.csv", "application_test.csv"],
}

REFERENCE_EXCLUDED_COLUMNS = {
    "application_test.csv": {"TARGET"},
}

BRONZE_REQUIRED_COLUMNS = {
    "application_train.csv": ["SK_ID_CURR", "TARGET"],
    "application_test.csv": ["SK_ID_CURR"],
    "bureau.csv": ["SK_ID_CURR", "SK_ID_BUREAU"],
    "bureau_balance.csv": ["SK_ID_BUREAU", "MONTHS_BALANCE"],
    "previous_application.csv": ["SK_ID_PREV", "SK_ID_CURR"],
    "POS_CASH_balance.csv": ["SK_ID_PREV", "SK_ID_CURR"],
    "credit_card_balance.csv": ["SK_ID_PREV", "SK_ID_CURR"],
    "installments_payments.csv": ["SK_ID_PREV", "SK_ID_CURR"],
}


@lru_cache(maxsize=1)
def load_reference_schema():
    """Load the reference column description file shipped with the repository."""

    schema_by_file = {}

    for table in RAW_TABLES:
        schema_by_file[table["file_name"]] = {
            "expected_columns": [],
            "column_descriptions": {},
        }

    with REFERENCE_SCHEMA_PATH.open("r", encoding="cp1252", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            reference_table = row["Table"].strip()
            column_name = row["Row"].strip()
            description = row["Description"].strip()

            file_names = REFERENCE_TABLE_MAPPING.get(reference_table, [reference_table])
            for file_name in file_names:
                if file_name not in schema_by_file:
                    continue
                if column_name in REFERENCE_EXCLUDED_COLUMNS.get(file_name, set()):
                    continue

                schema_by_file[file_name]["expected_columns"].append(column_name)
                schema_by_file[file_name]["column_descriptions"][column_name] = description

    return schema_by_file


def evaluate_schema(table, actual_columns):
    """Compare actual columns against the reference schema for the bronze input file."""

    reference_schema = load_reference_schema().get(table["file_name"], {})
    expected_columns = reference_schema.get("expected_columns", [])
    required_columns = BRONZE_REQUIRED_COLUMNS.get(table["file_name"], [])

    actual_set = set(actual_columns)
    expected_set = set(expected_columns)

    missing_required_columns = sorted(
        column for column in required_columns if column not in actual_set
    )
    missing_expected_columns = sorted(
        column for column in expected_columns if column not in actual_set
    )
    unexpected_columns = sorted(column for column in actual_columns if column not in expected_set)

    schema_status = "ok"
    if missing_required_columns:
        schema_status = "error"
    elif missing_expected_columns or unexpected_columns:
        schema_status = "warning"

    return {
        "schema_status": schema_status,
        "expected_column_count": len(expected_columns),
        "required_columns": required_columns,
        "missing_required_columns": missing_required_columns,
        "missing_expected_columns": missing_expected_columns,
        "unexpected_columns": unexpected_columns,
        "expected_columns": expected_columns,
    }


@lru_cache(maxsize=1)
def load_manual_column_mapping():
    """Load manual bronze column overrides from the versioned reference CSV."""

    mapping = {}
    with BRONZE_COLUMN_MAPPING_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            file_name = row["file_name"].strip()
            source_column = row["source_column"].strip()
            mapping[(file_name, source_column)] = {
                "file_name": file_name,
                "source_column": source_column,
                "reference_column": row["reference_column"].strip() or None,
                "bronze_column": row["bronze_column"].strip() or None,
                "bronze_type": row["bronze_type"].strip() or None,
                "notes": row["notes"].strip() or None,
            }
    return mapping


@lru_cache(maxsize=1)
def load_schema_mapping():
    """Load the explicit bronze schema mapping for type and nullable enforcement."""

    mapping = {}
    with BRONZE_SCHEMA_MAPPING_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            file_name = row["file_name"].strip()
            source_column = row["source_column"].strip()
            mapping[(file_name, source_column)] = {
                "bronze_type": row["bronze_type"].strip() or None,
                "bronze_nullable": row["bronze_nullable"].strip() or None,
            }
    return mapping


@lru_cache(maxsize=1)
def load_sentinel_mapping():
    """Load explicit sentinel replacement rules for bronze source columns."""

    mapping = {}
    with BRONZE_SENTINEL_MAPPING_PATH.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row["is_active"].strip().lower() != "true":
                continue

            file_name = row["file_name"].strip()
            source_column = row["source_column"].strip()
            mapping[(file_name, source_column)] = {
                "sentinel_sql": normalize_literal_sql(row["sentinel_sql"].strip()),
                "replacement_sql": normalize_literal_sql(row["replacement_sql"].strip()),
                "notes": row["notes"].strip() or None,
            }
    return mapping


def normalize_literal_sql(value: str) -> str:
    """Return a safe SQL literal for sentinel mapping values."""

    if value.upper() == "NULL":
        return "NULL"
    return quote_string(value)


def infer_identifier_nullable(source_column, reference_column):
    """Return the default bronze nullability for identifier-like columns."""

    if source_column.startswith("SK_ID_"):
        return "NO"
    if reference_column and (
        reference_column.startswith("SK_ID_") or reference_column == "SK_BUREAU_ID"
    ):
        return "NO"
    return "YES"


def resolve_column_mapping(table, source_column):
    """Resolve the bronze target name and metadata for a source column."""

    file_name = table["file_name"]
    manual_mapping = load_manual_column_mapping().get((file_name, source_column))
    schema_mapping = load_schema_mapping().get((file_name, source_column), {})
    reference_schema = load_reference_schema().get(file_name, {})
    reference_columns = set(reference_schema.get("expected_columns", []))

    if manual_mapping is not None:
        reference_column = manual_mapping["reference_column"] or source_column
        bronze_column = manual_mapping["bronze_column"] or snake_case(reference_column)
        return {
            "source_column": source_column,
            "reference_column": reference_column,
            "bronze_column": bronze_column,
            "bronze_type": schema_mapping.get("bronze_type") or manual_mapping["bronze_type"],
            "bronze_nullable": schema_mapping.get("bronze_nullable")
            or infer_identifier_nullable(source_column, reference_column),
            "mapping_source": "manual_override",
            "notes": manual_mapping["notes"],
        }

    if source_column in reference_columns:
        return {
            "source_column": source_column,
            "reference_column": source_column,
            "bronze_column": snake_case(source_column),
            "bronze_type": schema_mapping.get("bronze_type"),
            "bronze_nullable": schema_mapping.get("bronze_nullable")
            or infer_identifier_nullable(source_column, source_column),
            "mapping_source": "reference_default",
            "notes": None,
        }

    return {
        "source_column": source_column,
        "reference_column": None,
        "bronze_column": snake_case(source_column),
        "bronze_type": schema_mapping.get("bronze_type"),
        "bronze_nullable": schema_mapping.get("bronze_nullable")
        or infer_identifier_nullable(source_column, None),
        "mapping_source": "fallback_snake_case",
        "notes": None,
    }
