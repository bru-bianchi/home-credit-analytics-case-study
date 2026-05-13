"""Structural profiling and JSON reporting for raw CSV files."""

import csv
import json
from datetime import datetime

from .config import RAW_TABLES, RAW_VALIDATION_VERSION

def determine_validation_status(result):
    """Classify the raw file validation result."""

    if not result["exists"]:
        return "missing"

    if not result["read_success"]:
        return "invalid"

    if result["errors"]:
        return "invalid"

    return "valid"


def get_file_identity(raw_dir, table):
    """Collect lightweight file identity fields used for cache lookup."""

    file_path = raw_dir / table["file_name"]
    exists = file_path.exists()
    stat = file_path.stat() if exists else None
    file_size_bytes = stat.st_size if stat else None
    file_modified_at_ns = stat.st_mtime_ns if stat else None
    file_fingerprint = (
        f"{file_path}|{file_size_bytes}|{file_modified_at_ns}" if exists else None
    )
    return {
        "path": str(file_path),
        "exists": exists,
        "file_size_bytes": file_size_bytes,
        "file_modified_at_ns": file_modified_at_ns,
        "file_fingerprint": file_fingerprint,
        "validation_version": RAW_VALIDATION_VERSION,
    }


def profile_file(raw_dir, table, cached_result=None):
    """Check if the file exists, can be read, and has a basic valid structure."""

    file_identity = get_file_identity(raw_dir, table)
    file_path = raw_dir / table["file_name"]

    if cached_result is not None:
        result = dict(cached_result)
        result.update(file_identity)
        result["skipped_cached_validation"] = True
        return result

    result = {
        "table_name": table["table_name"],
        "file_name": table["file_name"],
        "path": file_identity["path"],
        "exists": file_identity["exists"],
        "read_success": False,
        "validation_status": "not_validated",
        "row_count": 0,
        "column_count": 0,
        "column_names": [],
        "file_size_bytes": file_identity["file_size_bytes"],
        "file_modified_at_ns": file_identity["file_modified_at_ns"],
        "file_fingerprint": file_identity["file_fingerprint"],
        "validation_version": file_identity["validation_version"],
        "skipped_cached_validation": False,
        "errors": [],
    }

    if not file_path.exists():
        result["errors"].append("file_not_found")
        result["validation_status"] = determine_validation_status(result)
        return result

    try:
        with file_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader, None)

            if not header:
                result["errors"].append("empty_file")
                result["validation_status"] = determine_validation_status(result)
                return result

            result["column_names"] = header
            result["column_count"] = len(header)

            column_samples = {column: [] for column in header}

            for row in reader:
                result["row_count"] += 1

                if len(row) != len(header):
                    result["errors"].append("inconsistent_row_length")
                    continue

                for column_name, value in zip(header, row):
                    if len(column_samples[column_name]) < 20:
                        column_samples[column_name].append(value)


            result["read_success"] = True
            result["validation_status"] = determine_validation_status(result)
            return result

    except UnicodeDecodeError:
        result["errors"].append("encoding_error")
        result["validation_status"] = determine_validation_status(result)
        return result
    except Exception as exc:
        result["errors"].append(f"read_error:{type(exc).__name__}")
        result["validation_status"] = determine_validation_status(result)
        return result


def build_ingestion_report(raw_dir, cached_validations=None):
    """Generate a simple metadata report for all expected raw files."""

    tables = []
    cached_validations = cached_validations or {}
    for table in RAW_TABLES:
        tables.append(
            profile_file(
                raw_dir,
                table,
                cached_result=cached_validations.get(table["table_name"]),
            )
        )

    return {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "raw_directory": str(raw_dir),
        "table_count_expected": len(RAW_TABLES),
        "table_count_found": sum(1 for table in tables if table["exists"]),
        "table_count_read_success": sum(1 for table in tables if table["read_success"]),
        "table_count_validation_passed": sum(
            1 for table in tables if table["validation_status"] == "valid"
        ),
        "table_count_validation_failed": sum(
            1 for table in tables if table["validation_status"] == "invalid"
        ),
        "table_count_missing": sum(
            1 for table in tables if table["validation_status"] == "missing"
        ),
        "table_count_skipped_cached_validation": sum(
            1 for table in tables if table["skipped_cached_validation"]
        ),
        "tables": tables,
    }


def write_report(report, output_path):
    """Save the ingestion report as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
