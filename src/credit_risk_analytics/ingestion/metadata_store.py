"""DuckDB persistence and cache reuse for raw ingestion validation metadata."""

import json
from datetime import datetime
from uuid import uuid4

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

    connection.execute("CREATE SCHEMA IF NOT EXISTS metadados;")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadados.raw_validation_runs (
            run_id VARCHAR,
            started_at_utc TIMESTAMP,
            raw_directory VARCHAR,
            database_path VARCHAR,
            table_count_expected INTEGER,
            table_count_found INTEGER,
            table_count_read_success INTEGER,
            table_count_validation_passed INTEGER,
            table_count_validation_failed INTEGER,
            table_count_missing INTEGER,
            table_count_skipped_cached_validation INTEGER
        );
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadados.raw_validation_files (
            run_id VARCHAR,
            validated_at_utc TIMESTAMP,
            table_name VARCHAR,
            file_name VARCHAR,
            file_path VARCHAR,
            file_exists BOOLEAN,
            read_success BOOLEAN,
            validation_status VARCHAR,
            row_count INTEGER,
            column_count INTEGER,
            file_size_bytes BIGINT,
            file_modified_at_ns BIGINT,
            file_fingerprint VARCHAR,
            validation_version VARCHAR,
            skipped_cached_validation BOOLEAN,
            column_names_json VARCHAR,
            errors_json VARCHAR
        );
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadados.raw_validation_run_files (
            run_id VARCHAR,
            table_name VARCHAR,
            file_name VARCHAR,
            file_path VARCHAR,
            file_fingerprint VARCHAR,
            validation_version VARCHAR,
            validation_status VARCHAR,
            used_cached_validation BOOLEAN
        );
        """
    )
def save_metadata(connection, run_id, started_at_utc, raw_dir, database_path, report):
    """Persist raw validation metadata inside DuckDB."""

    connection.execute(
        """
        INSERT INTO metadados.raw_validation_runs (
            run_id,
            started_at_utc,
            raw_directory,
            database_path,
            table_count_expected,
            table_count_found,
            table_count_read_success,
            table_count_validation_passed,
            table_count_validation_failed,
            table_count_missing,
            table_count_skipped_cached_validation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            started_at_utc,
            str(raw_dir),
            str(database_path),
            report["table_count_expected"],
            report["table_count_found"],
            report["table_count_read_success"],
            report["table_count_validation_passed"],
            report["table_count_validation_failed"],
            report["table_count_missing"],
            report["table_count_skipped_cached_validation"],
        ],
    )

    for table_report in report["tables"]:
        if not table_report["skipped_cached_validation"]:
            connection.execute(
                """
                INSERT INTO metadados.raw_validation_files (
                    run_id,
                    validated_at_utc,
                    table_name,
                    file_name,
                    file_path,
                    file_exists,
                    read_success,
                    validation_status,
                    row_count,
                    column_count,
                    file_size_bytes,
                    file_modified_at_ns,
                    file_fingerprint,
                    validation_version,
                    skipped_cached_validation,
                    column_names_json,
                    errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    started_at_utc,
                    table_report["table_name"],
                    table_report["file_name"],
                    table_report["path"],
                    table_report["exists"],
                    table_report["read_success"],
                    table_report["validation_status"],
                    table_report["row_count"],
                    table_report["column_count"],
                    table_report["file_size_bytes"],
                    table_report["file_modified_at_ns"],
                    table_report["file_fingerprint"],
                    table_report["validation_version"],
                    table_report["skipped_cached_validation"],
                    json.dumps(table_report["column_names"]),
                    json.dumps(table_report["errors"]),
                ],
            )

        connection.execute(
            """
            INSERT INTO metadados.raw_validation_run_files (
                run_id,
                table_name,
                file_name,
                file_path,
                file_fingerprint,
                validation_version,
                validation_status,
                used_cached_validation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                table_report["table_name"],
                table_report["file_name"],
                table_report["path"],
                table_report["file_fingerprint"],
                table_report["validation_version"],
                table_report["validation_status"],
                table_report["skipped_cached_validation"],
            ],
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
                    """
                    SELECT
                        table_name,
                        file_name,
                        file_path,
                        file_exists,
                        read_success,
                        validation_status,
                        row_count,
                        column_count,
                        file_size_bytes,
                        file_modified_at_ns,
                        file_fingerprint,
                        validation_version,
                        column_names_json,
                        errors_json
                    FROM metadados.raw_validation_files
                    WHERE table_name = ?
                      AND file_fingerprint = ?
                      AND validation_version = ?
                      AND validation_status = 'valid'
                    ORDER BY validated_at_utc DESC
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

            cached_results[table["table_name"]] = {
                "table_name": row[0],
                "file_name": row[1],
                "path": row[2],
                "exists": row[3],
                "read_success": row[4],
                "validation_status": row[5],
                "row_count": row[6],
                "column_count": row[7],
                "file_size_bytes": row[8],
                "file_modified_at_ns": row[9],
                "file_fingerprint": row[10],
                "validation_version": row[11],
                "column_names": json.loads(row[13]),
                "errors": json.loads(row[14]),
            }

        return cached_results
    finally:
        connection.close()
