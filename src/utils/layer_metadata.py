"""Generic helpers to build and persist pipeline layer run reports."""

from __future__ import annotations

from uuid import uuid4

from .metadata_store import create_pipeline_events_table, insert_pipeline_event


SUCCESS_TABLE_STATUSES = ("success", "skipped_cached_transformation")


def create_layer_metadata_tables(connection):
    """Create shared metadata tables used by transformed layers."""

    create_pipeline_events_table(connection)


def initialize_layer_run_report(
    *,
    started_at_utc,
    warehouse_path,
    output_directory_key: str,
    output_directory,
    table_names,
    extra_fields: dict | None = None,
):
    """Create the common run report structure for transformed layers."""

    run_report = {
        "run_id": str(uuid4()),
        "generated_at_utc": started_at_utc.isoformat() + "Z",
        "warehouse_path": str(warehouse_path),
        output_directory_key: str(output_directory),
        "table_count_selected": len(table_names),
        "table_count_succeeded": 0,
        "table_count_failed": 0,
        "run_status": "running",
        "tables": [],
    }
    if extra_fields:
        run_report.update(extra_fields)
    return run_report


def append_layer_table_report(run_report, table_report: dict):
    """Append one table report to the current layer run report."""

    run_report["tables"].append(table_report)
    return table_report


def finalize_layer_run_report(run_report, success_statuses=SUCCESS_TABLE_STATUSES):
    """Finalize standard success and failure counters for a layer run."""

    run_report["table_count_succeeded"] = sum(
        1 for table in run_report["tables"] if table["table_status"] in success_statuses
    )
    run_report["table_count_failed"] = sum(
        1 for table in run_report["tables"] if table["table_status"] == "failed"
    )
    run_report["run_status"] = (
        "partial_failure" if run_report["table_count_failed"] > 0 else "success"
    )
    return run_report


def finalize_layer_dry_run_report(run_report, planned_status="planned"):
    """Finalize a dry run report without treating pending tables as failures."""

    run_report["table_count_succeeded"] = run_report["table_count_selected"]
    run_report["table_count_failed"] = 0
    run_report["run_status"] = planned_status
    for table in run_report["tables"]:
        if table["table_status"] == "pending":
            table["table_status"] = planned_status
    return run_report


def build_skipped_cached_count(run_report):
    """Count how many tables reused a cached transformation."""

    return sum(
        1
        for table in run_report["tables"]
        if table["table_status"] == "skipped_cached_transformation"
    )


def persist_layer_run_report(
    connection,
    run_report,
    finished_at_utc,
    *,
    layer: str,
    run_entity_name: str,
    run_process_version: str,
    output_directory_key: str,
    build_run_details,
    build_table_event_payload,
):
    """Persist one layer run plus all table events in DuckDB."""

    insert_pipeline_event(
        connection,
        run_id=run_report["run_id"],
        event_ts_utc=finished_at_utc,
        layer=layer,
        entity_type="run",
        entity_name=run_entity_name,
        status=run_report["run_status"],
        started_at_utc=run_report["generated_at_utc"],
        finished_at_utc=finished_at_utc,
        warehouse_path=run_report["warehouse_path"],
        output_directory=run_report[output_directory_key],
        process_version=run_process_version,
        used_cached_result=False,
        details=build_run_details(run_report),
    )

    for table_report in run_report["tables"]:
        event_payload = build_table_event_payload(run_report, table_report)
        insert_pipeline_event(
            connection,
            run_id=run_report["run_id"],
            event_ts_utc=finished_at_utc,
            layer=layer,
            entity_type="table",
            entity_name=table_report["table_name"],
            status=table_report["table_status"],
            started_at_utc=run_report["generated_at_utc"],
            finished_at_utc=finished_at_utc,
            warehouse_path=run_report["warehouse_path"],
            output_directory=run_report[output_directory_key],
            **event_payload,
        )
