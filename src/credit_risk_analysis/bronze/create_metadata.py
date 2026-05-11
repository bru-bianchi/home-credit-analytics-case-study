"""Warehouse metadata persistence for bronze transformation runs."""

from __future__ import annotations

from uuid import uuid4

from utils.metadata_store import (
    create_pipeline_events_table,
    insert_pipeline_event,
)


def create_metadata_tables(connection):
    """Create metadata tables used to track bronze transformation executions."""

    create_pipeline_events_table(connection)


def initialize_run_report(started_at_utc, warehouse_path, bronze_directory, table_names):
    """Create the bronze run report structure."""

    return {
        "run_id": str(uuid4()),
        "generated_at_utc": started_at_utc.isoformat() + "Z",
        "warehouse_path": str(warehouse_path),
        "bronze_directory": str(bronze_directory),
        "table_count_selected": len(table_names),
        "table_count_succeeded": 0,
        "table_count_failed": 0,
        "run_status": "running",
        "tables": [],
    }


def append_table_report(run_report, plan):
    """Append one table plan to the run report before execution."""

    table_report = {
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
    }
    run_report["tables"].append(table_report)
    return table_report


def finalize_run_report(run_report):
    """Finalize aggregated run counters and status."""

    run_report["table_count_succeeded"] = sum(
        1
        for table in run_report["tables"]
        if table["table_status"] in ("success", "skipped_cached_transformation")
    )
    run_report["table_count_failed"] = sum(
        1 for table in run_report["tables"] if table["table_status"] == "failed"
    )
    if run_report["table_count_failed"] > 0:
        run_report["run_status"] = "partial_failure"
    else:
        run_report["run_status"] = "success"
    return run_report


def finalize_dry_run_report(run_report):
    """Finalize a dry-run report without treating pending tables as failures."""

    run_report["table_count_succeeded"] = run_report["table_count_selected"]
    run_report["table_count_failed"] = 0
    run_report["run_status"] = "planned"
    for table in run_report["tables"]:
        if table["table_status"] == "pending":
            table["table_status"] = "planned"
    return run_report


def persist_run_report(connection, run_report, finished_at_utc):
    """Persist one bronze transformation run and its tables in DuckDB."""

    insert_pipeline_event(
        connection,
        run_id=run_report["run_id"],
        event_ts_utc=finished_at_utc,
        layer="bronze",
        entity_type="run",
        entity_name="bronze_transformation",
        status=run_report["run_status"],
        started_at_utc=run_report["generated_at_utc"],
        finished_at_utc=finished_at_utc,
        warehouse_path=run_report["warehouse_path"],
        output_directory=run_report["bronze_directory"],
        process_version="bronze_run_v1",
        used_cached_result=False,
        details={
            "table_count_selected": run_report["table_count_selected"],
            "table_count_succeeded": run_report["table_count_succeeded"],
            "table_count_failed": run_report["table_count_failed"],
        },
    )

    for table_report in run_report["tables"]:
        schema_check = table_report.get("schema_check") or {}
        insert_pipeline_event(
            connection,
            run_id=run_report["run_id"],
            event_ts_utc=finished_at_utc,
            layer="bronze",
            entity_type="table",
            entity_name=table_report["table_name"],
            status=table_report["table_status"],
            started_at_utc=run_report["generated_at_utc"],
            finished_at_utc=finished_at_utc,
            warehouse_path=run_report["warehouse_path"],
            output_directory=run_report["bronze_directory"],
            source_name=table_report["file_name"],
            artifact_path=table_report["parquet_path"],
            process_version=table_report["bronze_transformation_version"],
            row_count=table_report["bronze_row_count"],
            column_count=table_report["bronze_column_count"],
            error_message=table_report["error_message"],
            used_cached_result=table_report["used_cached_transformation"],
            details={
                "raw_file_fingerprint": table_report["raw_file_fingerprint"],
                "planned_schema": table_report["planned_schema"],
                "schema_check": schema_check,
                "reference_schema_check": table_report["reference_schema_check"],
                "boolean_candidates": table_report["boolean_candidates"],
                "sentinel_columns": table_report["sentinel_columns"],
                "column_rules": table_report["column_rules"],
                "validation_warnings": table_report["validation_warnings"],
            },
        )
