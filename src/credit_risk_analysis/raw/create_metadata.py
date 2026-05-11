"""DuckDB persistence and cache reuse for raw ingestion validation metadata."""

import json
from datetime import datetime
from uuid import uuid4

from utils.metadata_store import (
    RAW_VALIDATION_EVENTS_TABLE,
    create_raw_validation_events_table,
    insert_raw_validation_event,
)

from .config import RAW_TABLES, RAW_VALIDATION_VERSION
from .raw_files_validator import get_file_identity


def open_warehouse_connection(database_path, read_only=False):
    """Open the local DuckDB warehouse with a clear lock error."""

    try:
        import duckdb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "duckdb_not_installed: install dependencies with `pip install -r requirements.txt`."
        ) from exc

    try:
        return duckdb.connect(str(database_path), read_only=read_only)
    except Exception as exc:
        message = str(exc)
        if "Could not set lock on file" in message:
            raise RuntimeError(
                "duckdb_database_locked: feche qualquer sessão aberta do DuckDB CLI, DuckDB UI "
                f"ou Python que esteja usando '{database_path}' e execute a ingestão novamente."
            ) from exc
        raise


def create_metadata_tables(connection):
    """Create metadata tables used to track raw validation executions."""

    create_raw_validation_events_table(connection)


def save_metadata(connection, run_id, started_at_utc, raw_dir, database_path, report):
    """Persist raw validation metadata inside DuckDB."""

    run_status = (
        "partial_failure"
        if report["table_count_validation_failed"] > 0 or report["table_count_missing"] > 0
        else "success"
    )
    insert_raw_validation_event(
        connection,
        run_id=run_id,
        event_ts_utc=started_at_utc,
        entity_type="run",
        entity_name="raw_validation",
        status=run_status,
        started_at_utc=started_at_utc,
        finished_at_utc=started_at_utc,
        warehouse_path=str(database_path),
        output_directory=str(raw_dir),
        process_version=RAW_VALIDATION_VERSION,
        used_cached_result=False,
        details={
            "table_count_expected": report["table_count_expected"],
            "table_count_found": report["table_count_found"],
            "table_count_read_success": report["table_count_read_success"],
            "table_count_validation_passed": report["table_count_validation_passed"],
            "table_count_validation_failed": report["table_count_validation_failed"],
            "table_count_missing": report["table_count_missing"],
            "table_count_skipped_cached_validation": report[
                "table_count_skipped_cached_validation"
            ],
            "raw_directory": str(raw_dir),
            "database_path": str(database_path),
        },
    )

    for table_report in report["tables"]:
        error_message = (
            json.dumps(table_report["errors"]) if table_report["errors"] else None
        )
        insert_raw_validation_event(
            connection,
            run_id=run_id,
            event_ts_utc=started_at_utc,
            entity_type="file",
            entity_name=table_report["table_name"],
            status=table_report["validation_status"],
            started_at_utc=started_at_utc,
            finished_at_utc=started_at_utc,
            warehouse_path=str(database_path),
            output_directory=str(raw_dir),
            source_name=table_report["file_name"],
            artifact_path=table_report["path"],
            file_fingerprint=table_report["file_fingerprint"],
            process_version=table_report["validation_version"],
            row_count=table_report["row_count"],
            column_count=table_report["column_count"],
            error_message=error_message,
            used_cached_result=table_report["skipped_cached_validation"],
            details={
                "file_exists": table_report["exists"],
                "read_success": table_report["read_success"],
                "file_size_bytes": table_report["file_size_bytes"],
                "file_modified_at_ns": table_report["file_modified_at_ns"],
                "column_names": table_report["column_names"],
                "errors": table_report["errors"],
            },
        )


def persist_raw_validation_report(raw_dir, database_path, report):
    """Persist a precomputed raw validation report in DuckDB."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    started_at_utc = datetime.utcnow().replace(microsecond=0)
    run_id = str(uuid4())

    connection = open_warehouse_connection(database_path)
    create_metadata_tables(connection)

    save_metadata(
        connection=connection,
        run_id=run_id,
        started_at_utc=started_at_utc,
        raw_dir=raw_dir,
        database_path=database_path,
        report=report,
    )
    connection.close()

    return {
        "run_id": run_id,
        "started_at_utc": started_at_utc.isoformat() + "Z",
        "database_path": str(database_path),
        "validated_table_count": report["table_count_expected"],
        "valid_table_count": report["table_count_validation_passed"],
        "invalid_table_count": report["table_count_validation_failed"],
        "missing_table_count": report["table_count_missing"],
        "skipped_cached_validation_count": report["table_count_skipped_cached_validation"],
        "validation_report": report,
    }


def load_cached_validation_results(raw_dir, database_path):
    """Load reusable successful validation results for unchanged raw files."""

    if not database_path.exists():
        return {}

    connection = open_warehouse_connection(database_path, read_only=True)
    try:
        cached_results = {}

        for table in RAW_TABLES:
            file_identity = get_file_identity(raw_dir, table)
            if not file_identity["exists"]:
                continue

            try:
                row = connection.execute(
                    f"""
                    SELECT
                        entity_name,
                        source_name,
                        artifact_path,
                        status,
                        row_count,
                        column_count,
                        file_fingerprint,
                        process_version,
                        used_cached_result,
                        details_json
                    FROM {RAW_VALIDATION_EVENTS_TABLE}
                    WHERE entity_type = 'file'
                      AND entity_name = ?
                      AND file_fingerprint = ?
                      AND process_version = ?
                      AND status = 'valid'
                    ORDER BY event_ts_utc DESC
                    LIMIT 1
                    """,
                    [
                        table["table_name"],
                        file_identity["file_fingerprint"],
                        RAW_VALIDATION_VERSION,
                    ],
                ).fetchone()
            except Exception:
                return {}

            if row is None:
                continue

            details = json.loads(row[9]) if row[9] else {}
            cached_results[table["table_name"]] = {
                "table_name": row[0],
                "file_name": row[1],
                "path": row[2],
                "exists": details.get("file_exists"),
                "read_success": details.get("read_success"),
                "validation_status": row[3],
                "row_count": row[4],
                "column_count": row[5],
                "file_size_bytes": details.get("file_size_bytes"),
                "file_modified_at_ns": details.get("file_modified_at_ns"),
                "file_fingerprint": row[6],
                "validation_version": row[7],
                "skipped_cached_validation": row[8],
                "column_names": details.get("column_names", []),
                "errors": details.get("errors", []),
            }

        return cached_results
    finally:
        connection.close()
