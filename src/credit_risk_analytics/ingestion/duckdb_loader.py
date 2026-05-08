"""Load validated raw CSV files into DuckDB using Python."""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .file_catalog import RAW_TABLES
from .csv_profiler import build_ingestion_report
from .schema_registry import load_reference_schema


def quote_identifier(name):
    """Quote DuckDB identifiers safely."""

    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def create_metadata_tables(connection):
    """Create metadata tables used to track ingestion executions."""

    connection.execute("CREATE SCHEMA IF NOT EXISTS metadados;")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadados.ingestion_runs (
            run_id VARCHAR,
            started_at_utc TIMESTAMP,
            raw_directory VARCHAR,
            database_path VARCHAR,
            table_count_expected INTEGER,
            table_count_found INTEGER,
            table_count_read_success INTEGER,
            loaded_table_count INTEGER
        );
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadados.ingestion_run_tables (
            run_id VARCHAR,
            table_name VARCHAR,
            file_name VARCHAR,
            file_path VARCHAR,
            file_exists BOOLEAN,
            read_success BOOLEAN,
            loaded_to_raw_schema BOOLEAN,
            already_processed BOOLEAN,
            skipped_reason VARCHAR,
            schema_status VARCHAR,
            row_count INTEGER,
            column_count INTEGER,
            file_size_bytes BIGINT,
            inferred_types_json VARCHAR,
            missing_required_columns_json VARCHAR,
            missing_expected_columns_json VARCHAR,
            unexpected_columns_json VARCHAR,
            errors_json VARCHAR
        );
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS already_processed BOOLEAN;
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS skipped_reason VARCHAR;
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS schema_status VARCHAR;
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS inferred_types_json VARCHAR;
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS missing_required_columns_json VARCHAR;
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS missing_expected_columns_json VARCHAR;
        """
    )
    connection.execute(
        """
        ALTER TABLE metadados.ingestion_run_tables
        ADD COLUMN IF NOT EXISTS unexpected_columns_json VARCHAR;
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadados.source_schema_reference (
            file_name VARCHAR,
            column_name VARCHAR,
            description VARCHAR
        );
        """
    )


def refresh_source_schema_reference(connection):
    """Load the repository reference schema into DuckDB metadata tables."""

    reference_schema = load_reference_schema()
    connection.execute("DELETE FROM metadados.source_schema_reference;")

    for file_name, schema_info in reference_schema.items():
        for column_name in schema_info["expected_columns"]:
            connection.execute(
                """
                INSERT INTO metadados.source_schema_reference VALUES (?, ?, ?)
                """,
                [
                    file_name,
                    column_name,
                    schema_info["column_descriptions"].get(column_name),
                ],
            )


def was_file_already_processed(connection, file_path, file_size_bytes):
    """Check whether the same raw file was already loaded successfully before."""

    query = """
        SELECT 1
        FROM metadados.ingestion_run_tables
        WHERE file_path = ?
          AND file_size_bytes = ?
          AND loaded_to_raw_schema = TRUE
        LIMIT 1
    """
    result = connection.execute(query, [str(file_path), file_size_bytes]).fetchone()
    return result is not None


def save_metadata(
    connection,
    run_id,
    started_at_utc,
    raw_dir,
    database_path,
    report,
    loaded_tables,
    skipped_tables,
):
    """Persist ingestion metadata inside DuckDB."""

    loaded_table_names = {item["table_name"] for item in loaded_tables}
    skipped_tables_by_name = {item["table_name"]: item for item in skipped_tables}

    connection.execute(
        """
        INSERT INTO metadados.ingestion_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            started_at_utc,
            str(raw_dir),
            str(database_path),
            report["table_count_expected"],
            report["table_count_found"],
            report["table_count_read_success"],
            len(loaded_tables),
        ],
    )

    for table_report in report["tables"]:
        skipped_info = skipped_tables_by_name.get(table_report["table_name"], {})
        connection.execute(
            """
            INSERT INTO metadados.ingestion_run_tables VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                table_report["table_name"],
                table_report["file_name"],
                table_report["path"],
                table_report["exists"],
                table_report["read_success"],
                table_report["table_name"] in loaded_table_names,
                skipped_info.get("already_processed", False),
                skipped_info.get("skipped_reason"),
                table_report["schema_status"],
                table_report["row_count"],
                table_report["column_count"],
                table_report["file_size_bytes"],
                json.dumps(table_report["inferred_types"]),
                json.dumps(table_report["missing_required_columns"]),
                json.dumps(table_report["missing_expected_columns"]),
                json.dumps(table_report["unexpected_columns"]),
                json.dumps(table_report["errors"]),
            ],
        )


def load_raw_tables_to_duckdb(raw_dir, database_path):
    """Load all readable raw CSV files into a raw schema in DuckDB."""

    try:
        import duckdb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "duckdb_not_installed: install dependencies with `pip install -r requirements.txt`."
        ) from exc

    report = build_ingestion_report(raw_dir)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    started_at_utc = datetime.utcnow().replace(microsecond=0)
    run_id = str(uuid4())

    connection = duckdb.connect(str(database_path))
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    create_metadata_tables(connection)
    refresh_source_schema_reference(connection)

    loaded_tables = []
    skipped_tables = []

    for table in RAW_TABLES:
        table_name = table["table_name"]
        file_name = table["file_name"]
        file_path = raw_dir / file_name

        table_report = next(
            item for item in report["tables"] if item["table_name"] == table_name
        )
        if not table_report["read_success"]:
            skipped_tables.append(
                {
                    "table_name": table_name,
                    "already_processed": False,
                    "skipped_reason": "read_failed_or_missing",
                }
            )
            continue

        if table_report["schema_status"] == "error":
            skipped_tables.append(
                {
                    "table_name": table_name,
                    "already_processed": False,
                    "skipped_reason": "schema_error",
                }
            )
            continue

        if was_file_already_processed(
            connection, file_path=file_path, file_size_bytes=table_report["file_size_bytes"]
        ):
            skipped_tables.append(
                {
                    "table_name": table_name,
                    "already_processed": True,
                    "skipped_reason": "already_processed",
                }
            )
            continue

        quoted_table = quote_identifier(table_name)
        escaped_path = str(file_path).replace("'", "''")

        connection.execute(f"DROP TABLE IF EXISTS raw.{quoted_table};")
        connection.execute(
            f"""
            CREATE TABLE raw.{quoted_table} AS
            SELECT *
            FROM read_csv_auto('{escaped_path}', HEADER=TRUE);
            """
        )

        loaded_tables.append(
            {
                "table_name": table_name,
                "source_file": str(file_path),
            }
        )

    save_metadata(
        connection=connection,
        run_id=run_id,
        started_at_utc=started_at_utc,
        raw_dir=raw_dir,
        database_path=database_path,
        report=report,
        loaded_tables=loaded_tables,
        skipped_tables=skipped_tables,
    )
    connection.close()

    return {
        "run_id": run_id,
        "started_at_utc": started_at_utc.isoformat() + "Z",
        "database_path": str(database_path),
        "loaded_table_count": len(loaded_tables),
        "loaded_tables": loaded_tables,
        "already_processed_table_count": sum(
            1 for item in skipped_tables if item["already_processed"]
        ),
        "skipped_tables": skipped_tables,
        "skipped_table_count": report["table_count_expected"] - len(loaded_tables),
        "ingestion_report": report,
    }
