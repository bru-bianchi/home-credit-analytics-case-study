"""Warehouse metadata persistence for bronze transformation runs."""

from __future__ import annotations

from utils import (
    append_layer_table_report,
    create_layer_metadata_tables,
    finalize_layer_dry_run_report,
    finalize_layer_run_report,
    initialize_layer_run_report,
    persist_layer_run_report,
)


def create_metadata_tables(connection):
    """Create metadata tables used to track bronze transformation executions."""

    create_layer_metadata_tables(connection)


def initialize_run_report(started_at_utc, warehouse_path, bronze_directory, table_names):
    """Create the bronze run report structure."""

    return initialize_layer_run_report(
        started_at_utc=started_at_utc,
        warehouse_path=warehouse_path,
        output_directory_key="bronze_directory",
        output_directory=bronze_directory,
        table_names=table_names,
    )


def append_table_report(run_report, plan):
    """Append one table plan to the run report before execution."""

    return append_layer_table_report(
        run_report,
        {
            "table_name": plan["table_name"],
            "file_name": plan["file_name"],
            "parquet_path": str(plan["parquet_path"]),
            "raw_file_fingerprint": plan["raw_file_fingerprint"],
            "bronze_transformation_version": plan["bronze_transformation_version"],
            "reference_schema_check": plan["reference_schema_check"],
            "used_cached_transformation": False,
            "bronze_row_count": None,
            "bronze_column_count": plan["bronze_column_count"],
            "planned_schema": plan["normalized_output_schema"],
            "boolean_candidates": plan["boolean_candidates"],
            "sentinel_columns": plan["sentinel_columns"],
            "column_rules": plan["column_rules"],
            "validation_warnings": [],
            "table_status": "pending",
            "error_message": None,
            "schema_check": None,
        },
    )


def finalize_run_report(run_report):
    """Finalize aggregated run counters and status."""

    return finalize_layer_run_report(run_report)


def finalize_dry_run_report(run_report):
    """Finalize a dry-run report without treating pending tables as failures."""

    return finalize_layer_dry_run_report(run_report)


def persist_run_report(connection, run_report, finished_at_utc):
    """Persist one bronze transformation run and its tables in DuckDB."""

    persist_layer_run_report(
        connection,
        run_report,
        finished_at_utc,
        layer="bronze",
        run_entity_name="bronze_transformation",
        run_process_version="bronze_run_v1",
        output_directory_key="bronze_directory",
        build_run_details=lambda report: {
            "table_count_selected": report["table_count_selected"],
            "table_count_succeeded": report["table_count_succeeded"],
            "table_count_failed": report["table_count_failed"],
        },
        build_table_event_payload=lambda run, table_report: {
            "source_name": table_report["file_name"],
            "artifact_path": table_report["parquet_path"],
            "process_version": table_report["bronze_transformation_version"],
            "row_count": table_report["bronze_row_count"],
            "column_count": table_report["bronze_column_count"],
            "error_message": table_report["error_message"],
            "used_cached_result": table_report["used_cached_transformation"],
            "details": {
                "raw_file_fingerprint": table_report["raw_file_fingerprint"],
                "planned_schema": table_report["planned_schema"],
                "schema_check": table_report.get("schema_check") or {},
                "reference_schema_check": table_report["reference_schema_check"],
                "boolean_candidates": table_report["boolean_candidates"],
                "sentinel_columns": table_report["sentinel_columns"],
                "column_rules": table_report["column_rules"],
                "validation_warnings": table_report["validation_warnings"],
            },
        },
    )
