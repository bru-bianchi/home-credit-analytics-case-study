"""Reference schema checks based on the Home Credit column description file."""

import csv
from functools import lru_cache
from pathlib import Path

from .file_catalog import RAW_TABLES


PROJECT_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_SCHEMA_PATH = PROJECT_ROOT / "docs" / "references" / "HomeCredit_columns_description.csv"

REFERENCE_TABLE_MAPPING = {
    "application_{train|test}.csv": ["application_train.csv", "application_test.csv"],
}

REFERENCE_EXCLUDED_COLUMNS = {
    "application_test.csv": {"TARGET"},
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
    """Compare actual columns against the reference schema for the file."""

    reference_schema = load_reference_schema().get(table["file_name"], {})
    expected_columns = reference_schema.get("expected_columns", [])
    required_columns = table.get("required_columns", [])

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
