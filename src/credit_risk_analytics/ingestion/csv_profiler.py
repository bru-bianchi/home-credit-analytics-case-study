"""Simple checks for raw CSV files."""

import csv
import json
from datetime import datetime

from .file_catalog import RAW_TABLES
from .schema_registry import evaluate_schema


def infer_type(value):
    """Infer a basic type from a string value."""

    if value is None:
        return "empty"

    value = value.strip()
    if value == "":
        return "empty"

    try:
        int(value)
        return "integer"
    except ValueError:
        pass

    try:
        float(value)
        return "float"
    except ValueError:
        pass

    return "string"


def infer_column_type(samples):
    """Infer one basic type for the column from sampled values."""

    non_empty_types = []
    for value in samples:
        inferred = infer_type(value)
        if inferred != "empty":
            non_empty_types.append(inferred)

    if not non_empty_types:
        return "empty"

    if all(item == "integer" for item in non_empty_types):
        return "integer"

    if all(item in {"integer", "float"} for item in non_empty_types):
        return "float"

    if all(item == "string" for item in non_empty_types):
        return "string"

    return "mixed"


def profile_file(raw_dir, table):
    """Check if the file exists, can be read, and has a basic valid structure."""

    file_path = raw_dir / table["file_name"]
    result = {
        "table_name": table["table_name"],
        "file_name": table["file_name"],
        "path": str(file_path),
        "exists": file_path.exists(),
        "read_success": False,
        "row_count": 0,
        "column_count": 0,
        "column_names": [],
        "inferred_types": {},
        "schema_status": "not_checked",
        "expected_column_count": 0,
        "required_columns": table.get("required_columns", []),
        "missing_required_columns": [],
        "missing_expected_columns": [],
        "unexpected_columns": [],
        "expected_columns": [],
        "file_size_bytes": file_path.stat().st_size if file_path.exists() else None,
        "errors": [],
    }

    if not file_path.exists():
        result["errors"].append("file_not_found")
        return result

    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader, None)

            if not header:
                result["errors"].append("empty_file")
                return result

            result["column_names"] = header
            result["column_count"] = len(header)
            result.update(evaluate_schema(table, header))

            column_samples = {column: [] for column in header}

            for row in reader:
                result["row_count"] += 1

                if len(row) != len(header):
                    result["errors"].append("inconsistent_row_length")
                    continue

                for column_name, value in zip(header, row):
                    if len(column_samples[column_name]) < 20:
                        column_samples[column_name].append(value)

            for column_name in header:
                result["inferred_types"][column_name] = infer_column_type(
                    column_samples[column_name]
                )

            result["read_success"] = True
            if result["schema_status"] == "error":
                result["errors"].append("schema_error")
            elif result["schema_status"] == "warning":
                result["errors"].append("schema_warning")
            return result

    except UnicodeDecodeError:
        result["errors"].append("encoding_error")
        return result
    except Exception as exc:
        result["errors"].append(f"read_error:{type(exc).__name__}")
        return result


def build_ingestion_report(raw_dir):
    """Generate a simple metadata report for all expected raw files."""

    tables = []
    for table in RAW_TABLES:
        tables.append(profile_file(raw_dir, table))

    return {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "raw_directory": str(raw_dir),
        "table_count_expected": len(RAW_TABLES),
        "table_count_found": sum(1 for table in tables if table["exists"]),
        "table_count_read_success": sum(1 for table in tables if table["read_success"]),
        "tables": tables,
    }


def write_report(report, output_path):
    """Save the ingestion report as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
