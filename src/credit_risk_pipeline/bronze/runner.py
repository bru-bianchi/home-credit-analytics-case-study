"""Execution layer for raw-to-bronze transformation and warehouse ingestion."""

from __future__ import annotations

import json
from datetime import datetime

from credit_risk_pipeline.raw.config import RAW_TABLES
from utils import (
    close_duckdb_connection,
    ensure_runtime_directories,
    get_table_schema,
    normalize_schema_rows,
    open_duckdb_connection,
    table_exists,
    write_execution_report,
)
from utils.duckdb_utils import quote_identifier, quote_string, read_csv_relation
from utils.metadata_store import PIPELINE_EVENTS_TABLE

from .config import ARTIFACTS_DIR, BRONZE_DIR, WAREHOUSE_PATH
from .create_metadata import (
    append_table_report,
    create_metadata_tables,
    finalize_dry_run_report,
    finalize_run_report,
    initialize_run_report,
    persist_run_report,
)
from .transformation_builder import (
    build_bronze_transformation_signature,
    plan_table,
    read_raw_file_fingerprint,
    resolve_raw_csv_path,
)

def ensure_bronze_runtime_directories():
    """Ensure bronze output directories exist before planning or execution."""

    ensure_runtime_directories(BRONZE_DIR, ARTIFACTS_DIR, WAREHOUSE_PATH)


def select_bronze_tables(selected_tables=None):
    """Select which configured raw tables should be processed in this bronze run."""

    if not selected_tables:
        return RAW_TABLES

    selected = set(selected_tables)
    return [table for table in RAW_TABLES if table["table_name"] in selected]


def initialize_bronze_run_report(table_catalog):
    """Create the run report structure for the current bronze execution."""

    started_at_utc = datetime.utcnow().replace(microsecond=0)
    return initialize_run_report(
        started_at_utc=started_at_utc,
        warehouse_path=WAREHOUSE_PATH,
        bronze_directory=BRONZE_DIR,
        table_names=[table["table_name"] for table in table_catalog],
    )


def initialize_bronze_warehouse(dry_run=False):
    """Open and initialize the bronze warehouse structures when execution will write data."""

    if dry_run:
        return None

    connection = open_duckdb_connection(WAREHOUSE_PATH)
    connection.execute("CREATE SCHEMA IF NOT EXISTS bronze;")
    create_metadata_tables(connection)
    return connection


def open_profile_connection():
    """Open a temporary in-memory DuckDB connection for bronze planning."""

    try:
        import duckdb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "duckdb_not_installed: install dependencies with `pip install -r requirements.txt`."
        ) from exc

    return duckdb.connect()


def get_existing_bronze_schema(connection, table_name):
    """Return the current schema of a bronze table if it already exists."""

    return get_table_schema(connection, "bronze", table_name)


def collect_bronze_table_metrics(connection, table_name):
    """Collect row and column counts for a bronze table already loaded in the warehouse."""

    table_identifier = quote_identifier(table_name)
    row_count = connection.execute(
        f"SELECT COUNT(*) FROM bronze.{table_identifier}"
    ).fetchone()[0]
    schema_rows = get_existing_bronze_schema(connection, table_name) or []
    return {
        "bronze_row_count": row_count,
        "bronze_column_count": len(schema_rows),
    }


def load_latest_raw_table_metrics(connection, table_name):
    """Load the latest raw validation row and column counts for one source table."""

    if not table_exists(connection, "metadados", "raw_validation_events"):
        return None

    row = connection.execute(
        """
        SELECT row_count, column_count
        FROM metadados.raw_validation_events
        WHERE entity_type = 'file'
          AND entity_name = ?
        ORDER BY event_ts_utc DESC
        LIMIT 1
        """,
        [table_name],
    ).fetchone()
    if row is None:
        return None

    return {"raw_row_count": row[0], "raw_column_count": row[1]}


def compare_raw_and_bronze_metrics(plan, bronze_metrics, raw_metrics):
    """Compare the latest raw metrics with the bronze output metrics and return warnings."""

    if raw_metrics is None:
        return ["raw_metadata_not_found"]

    warnings = []
    if raw_metrics["raw_row_count"] != bronze_metrics["bronze_row_count"]:
        warnings.append(
            "raw_bronze_row_count_mismatch:"
            f"raw={raw_metrics['raw_row_count']}:bronze={bronze_metrics['bronze_row_count']}"
        )
    if raw_metrics["raw_column_count"] != bronze_metrics["bronze_column_count"]:
        warnings.append(
            "raw_bronze_column_count_mismatch:"
            f"raw={raw_metrics['raw_column_count']}:bronze={bronze_metrics['bronze_column_count']}"
        )
    if plan["bronze_column_count"] != bronze_metrics["bronze_column_count"]:
        warnings.append(
            "planned_bronze_column_count_mismatch:"
            f"planned={plan['bronze_column_count']}:loaded={bronze_metrics['bronze_column_count']}"
        )
    return warnings


def compare_schema_with_existing_table(connection, plan):
    """Ensure a bronze table keeps the same schema across reloads."""

    existing_schema = get_existing_bronze_schema(connection, plan["table_name"])
    planned_schema = plan["normalized_output_schema"]

    if existing_schema is None:
        return {"status": "new_table", "existing_schema": None, "planned_schema": planned_schema}

    normalized_existing_schema = normalize_schema_rows(existing_schema)
    if normalized_existing_schema != planned_schema:
        raise RuntimeError(
            "bronze_schema_mismatch: planned schema for "
            f"bronze.{plan['table_name']} differs from the existing warehouse table. "
            f"existing={normalized_existing_schema} planned={planned_schema}"
        )

    return {
        "status": "matched_existing_table",
        "existing_schema": normalized_existing_schema,
        "planned_schema": planned_schema,
    }


def load_latest_cached_bronze_result(connection, table_name):
    """Load the latest successful bronze metadata for one table, if available."""

    if not table_exists(connection, "metadados", "pipeline_events"):
        return None

    row = connection.execute(
        f"""
        SELECT details_json, process_version, row_count, column_count
        FROM {PIPELINE_EVENTS_TABLE}
        WHERE layer = 'bronze'
          AND entity_type = 'table'
          AND entity_name = ?
          AND status IN ('success', 'skipped_cached_transformation')
        ORDER BY rowid DESC
        LIMIT 1
        """,
        [table_name],
    ).fetchone()
    if row is None:
        return None

    details = json.loads(row[0]) if row[0] else {}
    return {
        "raw_file_fingerprint": details.get("raw_file_fingerprint"),
        "bronze_transformation_version": row[1],
        "planned_schema": [tuple(schema_row) for schema_row in details.get("planned_schema", [])],
        "bronze_row_count": row[2],
        "bronze_column_count": row[3],
        "validation_warnings": details.get("validation_warnings", []),
    }


def build_cache_context(table, bronze_transformation_version):
    """Build the lightweight cache inputs needed before bronze planning starts."""

    csv_path = resolve_raw_csv_path(table)
    return {
        "table_name": table["table_name"],
        "file_name": table["file_name"],
        "csv_path": csv_path,
        "parquet_path": BRONZE_DIR / f"{table['table_name']}.parquet",
        "raw_file_fingerprint": read_raw_file_fingerprint(csv_path),
        "bronze_transformation_version": bronze_transformation_version,
    }


def build_failed_table_report(table, error_message):
    """Build the standard failed table structure used in the bronze report."""

    return {
        "table_name": table["table_name"],
        "file_name": table["file_name"],
        "parquet_path": str(BRONZE_DIR / f"{table['table_name']}.parquet"),
        "raw_file_fingerprint": None,
        "bronze_transformation_version": None,
        "reference_schema_check": None,
        "used_cached_transformation": False,
        "bronze_row_count": None,
        "bronze_column_count": None,
        "planned_schema": None,
        "boolean_candidates": [],
        "sentinel_columns": [],
        "column_rules": [],
        "validation_warnings": [],
        "table_status": "failed",
        "error_message": error_message,
        "schema_check": None,
    }


def append_cached_table_report(run_report, cache_context, cached_result):
    """Append a cached bronze hit directly to the run report without replanning the table."""

    run_report["tables"].append(
        {
            "table_name": cache_context["table_name"],
            "file_name": cache_context["file_name"],
            "parquet_path": str(cache_context["parquet_path"]),
            "raw_file_fingerprint": cache_context["raw_file_fingerprint"],
            "bronze_transformation_version": cache_context["bronze_transformation_version"],
            "reference_schema_check": None,
            "used_cached_transformation": True,
            "bronze_row_count": cached_result["bronze_row_count"],
            "bronze_column_count": cached_result["bronze_column_count"],
            "planned_schema": cached_result["planned_schema"],
            "boolean_candidates": [],
            "sentinel_columns": [],
            "column_rules": [],
            "validation_warnings": cached_result["validation_warnings"],
            "table_status": "skipped_cached_transformation",
            "error_message": None,
            "schema_check": {
                "status": "cached_existing_table_reused",
                "existing_schema": cached_result["planned_schema"],
                "planned_schema": cached_result["planned_schema"],
            },
        }
    )


def try_append_cached_table_report(connection, run_report, table, bronze_transformation_version):
    """Append a cached table report when the current inputs fully match a previous bronze load."""

    cache_context = build_cache_context(table, bronze_transformation_version)
    if not cache_context["parquet_path"].exists():
        return False

    existing_schema = get_existing_bronze_schema(connection, cache_context["table_name"])
    if existing_schema is None:
        return False

    cached_result = load_latest_cached_bronze_result(connection, cache_context["table_name"])
    if cached_result is None:
        return False

    if cached_result["raw_file_fingerprint"] != cache_context["raw_file_fingerprint"]:
        return False
    if cached_result["bronze_transformation_version"] != bronze_transformation_version:
        return False
    if normalize_schema_rows(existing_schema) != cached_result["planned_schema"]:
        return False

    append_cached_table_report(run_report, cache_context, cached_result)
    return True


def build_bronze_plans(table_catalog, run_report, warehouse_connection, dry_run):
    """Build the bronze plans for the selected raw tables."""

    bronze_transformation_version = build_bronze_transformation_signature()
    planned_items = []
    profile_connection = None

    try:
        for table in table_catalog:
            try:
                if warehouse_connection is not None and not dry_run:
                    if try_append_cached_table_report(
                        warehouse_connection,
                        run_report,
                        table,
                        bronze_transformation_version,
                    ):
                        continue

                if profile_connection is None:
                    profile_connection = open_profile_connection()

                plan = plan_table(
                    profile_connection,
                    table,
                    bronze_transformation_version=bronze_transformation_version,
                )
                table_report = append_table_report(run_report, plan)
                planned_items.append((plan, table_report))
            except Exception as exc:
                run_report["tables"].append(
                    build_failed_table_report(table, f"{type(exc).__name__}: {exc}")
                )
    finally:
        close_duckdb_connection(profile_connection)

    return planned_items


def can_reuse_cached_plan(connection, plan):
    """Return cached bronze metadata when the current plan can safely reuse the previous load."""

    existing_schema = get_existing_bronze_schema(connection, plan["table_name"])
    if existing_schema is None:
        return None

    normalized_existing_schema = normalize_schema_rows(existing_schema)
    if normalized_existing_schema != plan["normalized_output_schema"]:
        return None

    cached_result = load_latest_cached_bronze_result(connection, plan["table_name"])
    if cached_result is None:
        return None

    if cached_result["raw_file_fingerprint"] != plan["raw_file_fingerprint"]:
        return None
    if cached_result["bronze_transformation_version"] != plan["bronze_transformation_version"]:
        return None
    if cached_result["planned_schema"] != plan["normalized_output_schema"]:
        return None

    return cached_result


def publish_bronze_table(connection, plan):
    """Publish one bronze table to parquet storage and to the warehouse."""

    parquet_sql = quote_string(plan["parquet_path"].as_posix())
    relation_sql = read_csv_relation(plan["csv_path"])
    table_identifier = quote_identifier(plan["table_name"])
    staging_table_identifier = quote_identifier(f"__staging_{plan['table_name']}")
    column_definitions = ",\n        ".join(
        f'{quote_identifier(column_name)} {column_type}'
        + (" NOT NULL" if nullable == "NO" else "")
        for column_name, column_type, nullable in plan["normalized_output_schema"]
    )

    connection.execute(
        f"""
        COPY (
            SELECT
{plan["select_sql"]}
            FROM {relation_sql}
        ) TO {parquet_sql} (FORMAT PARQUET, CODEC 'snappy');
        """
    )
    connection.execute(
        f"""
        DROP TABLE IF EXISTS bronze.{staging_table_identifier};
        CREATE TABLE bronze.{staging_table_identifier} (
            {column_definitions}
        );
        INSERT INTO bronze.{staging_table_identifier}
        SELECT *
        FROM read_parquet({parquet_sql});
        DROP TABLE IF EXISTS bronze.{table_identifier};
        ALTER TABLE bronze.{staging_table_identifier} RENAME TO {table_identifier};
        """
    )


def execute_bronze_plans(connection, planned_items):
    """Execute each planned bronze table and capture per-table status."""

    for plan, table_report in planned_items:
        try:
            cached_result = can_reuse_cached_plan(connection, plan)
            if cached_result is not None:
                table_report["schema_check"] = {
                    "status": "cached_existing_table_reused",
                    "existing_schema": plan["normalized_output_schema"],
                    "planned_schema": plan["normalized_output_schema"],
                }
                table_report["used_cached_transformation"] = True
                table_report["bronze_row_count"] = cached_result["bronze_row_count"]
                table_report["bronze_column_count"] = cached_result["bronze_column_count"]
                table_report["validation_warnings"] = cached_result["validation_warnings"]
                table_report["table_status"] = "skipped_cached_transformation"
                continue

            table_report["schema_check"] = compare_schema_with_existing_table(connection, plan)
            publish_bronze_table(connection, plan)
            bronze_metrics = collect_bronze_table_metrics(connection, plan["table_name"])
            raw_metrics = load_latest_raw_table_metrics(connection, plan["table_name"])
            table_report.update(bronze_metrics)
            table_report["validation_warnings"] = compare_raw_and_bronze_metrics(
                plan, bronze_metrics, raw_metrics
            )
            table_report["table_status"] = "success"
        except Exception as exc:
            table_report["table_status"] = "failed"
            table_report["error_message"] = f"{type(exc).__name__}: {exc}"


def write_bronze_dry_run_report(run_report):
    """Persist the bronze dry-run plan report to the artifacts directory."""

    finalize_dry_run_report(run_report)
    report_path = ARTIFACTS_DIR / "bronze_transformation_plan.json"
    report_path.write_text(json.dumps(run_report, indent=2), encoding="utf-8")
    return run_report


def write_bronze_execution_report(run_report):
    """Persist the bronze execution report and raise if any table failed."""

    return write_execution_report(
        run_report,
        ARTIFACTS_DIR,
        "bronze_transformation_report.json",
        "bronze_transformation_failed",
    )


def build_bronze_layer(selected_tables=None, dry_run=False):
    """Build bronze parquet files and load them into the local DuckDB warehouse."""

    ensure_bronze_runtime_directories()
    table_catalog = select_bronze_tables(selected_tables)
    run_report = initialize_bronze_run_report(table_catalog)
    warehouse_connection = None

    try:
        warehouse_connection = initialize_bronze_warehouse(dry_run=dry_run)
        planned_items = build_bronze_plans(
            table_catalog,
            run_report,
            warehouse_connection=warehouse_connection,
            dry_run=dry_run,
        )

        if dry_run:
            return write_bronze_dry_run_report(run_report)

        execute_bronze_plans(warehouse_connection, planned_items)
        finished_at_utc = datetime.utcnow().replace(microsecond=0)
        finalize_run_report(run_report)
        persist_run_report(warehouse_connection, run_report, finished_at_utc)
    finally:
        close_duckdb_connection(warehouse_connection)

    return write_bronze_execution_report(run_report)
