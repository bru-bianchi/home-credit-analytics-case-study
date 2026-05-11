"""Warehouse metadata persistence for silver transformation runs."""

from __future__ import annotations

from uuid import uuid4

from utils.metadata_store import (
    create_pipeline_events_table,
    insert_pipeline_event,
)


def create_metadata_tables(connection):
    """Create metadata tables used to track silver transformation executions."""

    create_pipeline_events_table(connection)


def initialize_run_report(started_at_utc, warehouse_path, silver_directory, sql_directory, table_names):
    """Create the silver run report structure."""

    return {
        "run_id": str(uuid4()),
        "generated_at_utc": started_at_utc.isoformat() + "Z",
        "warehouse_path": str(warehouse_path),
        "silver_directory": str(silver_directory),
        "sql_directory": str(sql_directory),
        "table_count_selected": len(table_names),
        "table_count_succeeded": 0,
        "table_count_failed": 0,
        "run_status": "running",
        "tables": [],
    }


def append_table_report(run_report, table_name, sql_file_name, parquet_path, silver_transformation_version):
    """Append one silver table plan to the run report before execution."""

    table_report = {
        "table_name": table_name,
        "sql_file_name": sql_file_name,
        "parquet_path": str(parquet_path),
        "silver_transformation_version": silver_transformation_version,
        "used_cached_transformation": False,
        "silver_row_count": None,
        "silver_column_count": None,
        "table_status": "pending",
        "error_message": None,
        "schema": None,
        "sql_fingerprint": None,
        "source_dependencies": [],
        "source_fingerprints": {},
        "table_fingerprint": None,
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
    run_report["run_status"] = (
        "partial_failure" if run_report["table_count_failed"] > 0 else "success"
    )
    return run_report


def persist_run_report(connection, run_report, finished_at_utc):
    """Persist one silver transformation run and its tables in DuckDB."""

    insert_pipeline_event(
        connection,
        run_id=run_report["run_id"],
        event_ts_utc=finished_at_utc,
        layer="silver",
        entity_type="run",
        entity_name="silver_transformation",
        status=run_report["run_status"],
        started_at_utc=run_report["generated_at_utc"],
        finished_at_utc=finished_at_utc,
        warehouse_path=run_report["warehouse_path"],
        output_directory=run_report["silver_directory"],
        process_version="silver_run_v1",
        used_cached_result=False,
        details={
            "sql_directory": run_report["sql_directory"],
            "table_count_selected": run_report["table_count_selected"],
            "table_count_succeeded": run_report["table_count_succeeded"],
            "table_count_failed": run_report["table_count_failed"],
            "table_count_skipped_cached_transformation": sum(
                1
                for table in run_report["tables"]
                if table["table_status"] == "skipped_cached_transformation"
            ),
        },
    )

    for table_report in run_report["tables"]:
        insert_pipeline_event(
            connection,
            run_id=run_report["run_id"],
            event_ts_utc=finished_at_utc,
            layer="silver",
            entity_type="table",
            entity_name=table_report["table_name"],
            status=table_report["table_status"],
            started_at_utc=run_report["generated_at_utc"],
            finished_at_utc=finished_at_utc,
            warehouse_path=run_report["warehouse_path"],
            output_directory=run_report["silver_directory"],
            source_name=table_report["sql_file_name"],
            artifact_path=table_report["parquet_path"],
            process_version=table_report["silver_transformation_version"],
            row_count=table_report["silver_row_count"],
            column_count=table_report["silver_column_count"],
            error_message=table_report["error_message"],
            used_cached_result=table_report["used_cached_transformation"],
            details={
                "schema": table_report["schema"],
                "sql_fingerprint": table_report["sql_fingerprint"],
                "source_dependencies": table_report["source_dependencies"],
                "source_fingerprints": table_report["source_fingerprints"],
                "table_fingerprint": table_report["table_fingerprint"],
            },
        )
