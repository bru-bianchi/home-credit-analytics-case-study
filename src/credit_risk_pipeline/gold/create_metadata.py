"""Warehouse metadata persistence for gold transformation runs."""

from __future__ import annotations

from utils import (
    append_layer_table_report,
    build_skipped_cached_count,
    create_layer_metadata_tables,
    finalize_layer_run_report,
    initialize_layer_run_report,
    persist_layer_run_report,
)


def create_metadata_tables(connection):
    """Create metadata tables used to track gold transformation executions."""

    create_layer_metadata_tables(connection)


def initialize_run_report(started_at_utc, warehouse_path, gold_directory, sql_directory, table_names):
    """Create the gold run report structure."""

    return initialize_layer_run_report(
        started_at_utc=started_at_utc,
        warehouse_path=warehouse_path,
        output_directory_key="gold_directory",
        output_directory=gold_directory,
        table_names=table_names,
        extra_fields={"sql_directory": str(sql_directory)},
    )


def append_table_report(run_report, table_name, sql_file_name, parquet_path, transformation_version):
    """Append one gold table plan to the run report before execution."""

    return append_layer_table_report(
        run_report,
        {
            "table_name": table_name,
            "sql_file_name": sql_file_name,
            "parquet_path": str(parquet_path),
            "gold_transformation_version": transformation_version,
            "used_cached_transformation": False,
            "gold_row_count": None,
            "gold_column_count": None,
            "table_status": "pending",
            "error_message": None,
            "schema": None,
            "sql_fingerprint": None,
            "source_dependencies": [],
            "source_fingerprints": {},
            "table_fingerprint": None,
        },
    )


def finalize_run_report(run_report):
    """Finalize aggregated run counters and status."""

    return finalize_layer_run_report(run_report)


def persist_run_report(connection, run_report, finished_at_utc):
    """Persist one gold transformation run and its tables in DuckDB."""

    persist_layer_run_report(
        connection,
        run_report,
        finished_at_utc,
        layer="gold",
        run_entity_name="gold_transformation",
        run_process_version="gold_run_v1",
        output_directory_key="gold_directory",
        build_run_details=lambda report: {
            "sql_directory": report["sql_directory"],
            "table_count_selected": report["table_count_selected"],
            "table_count_succeeded": report["table_count_succeeded"],
            "table_count_failed": report["table_count_failed"],
            "table_count_skipped_cached_transformation": build_skipped_cached_count(report),
        },
        build_table_event_payload=lambda run, table_report: {
            "source_name": table_report["sql_file_name"],
            "artifact_path": table_report["parquet_path"],
            "process_version": table_report["gold_transformation_version"],
            "row_count": table_report["gold_row_count"],
            "column_count": table_report["gold_column_count"],
            "error_message": table_report["error_message"],
            "used_cached_result": table_report["used_cached_transformation"],
            "details": {
                "schema": table_report["schema"],
                "sql_fingerprint": table_report["sql_fingerprint"],
                "source_dependencies": table_report["source_dependencies"],
                "source_fingerprints": table_report["source_fingerprints"],
                "table_fingerprint": table_report["table_fingerprint"],
            },
        },
    )
