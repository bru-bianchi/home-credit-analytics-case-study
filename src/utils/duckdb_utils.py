"""Reusable DuckDB helpers shared across project layers."""

from __future__ import annotations

from pathlib import Path


def quote_identifier(identifier: str) -> str:
    """Safely quote a SQL identifier for DuckDB."""

    return '"' + identifier.replace('"', '""') + '"'


def quote_string(value: str) -> str:
    """Safely quote a SQL string literal for DuckDB."""

    return "'" + value.replace("'", "''") + "'"


def read_csv_relation(csv_path) -> str:
    """Return a reusable DuckDB relation SQL fragment for a raw CSV."""

    return f"read_csv_auto({quote_string(csv_path.as_posix())}, header=true)"


def open_duckdb_connection(database_path: Path, read_only: bool = False):
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
                f"ou Python que esteja usando '{database_path}' e execute novamente."
            ) from exc
        raise


def close_duckdb_connection(connection) -> None:
    """Close a DuckDB connection when available."""

    if connection is not None:
        connection.close()


def read_sql_file(sql_path: Path) -> str:
    """Read a SQL script from disk."""

    return sql_path.read_text(encoding="utf-8")


def execute_sql_script(connection, sql_path: Path):
    """Execute a SQL script file in the current DuckDB connection."""

    return connection.execute(read_sql_file(sql_path))


def table_exists(connection, schema_name: str, table_name: str) -> bool:
    """Return whether a table currently exists in the DuckDB warehouse."""

    return bool(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = ?
              AND table_name = ?
            """,
            [schema_name, table_name],
        ).fetchone()[0]
    )


def get_table_schema(connection, schema_name: str, table_name: str):
    """Return the schema rows for an existing table."""

    if not table_exists(connection, schema_name, table_name):
        return None

    return connection.execute(
        f"DESCRIBE SELECT * FROM {quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    ).fetchall()


def export_table_to_parquet(connection, schema_name: str, table_name: str, parquet_path: Path) -> None:
    """Export a DuckDB table to parquet with snappy compression."""

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    connection.execute(
        f"""
        COPY (
            SELECT *
            FROM {quote_identifier(schema_name)}.{quote_identifier(table_name)}
        ) TO {quote_string(parquet_path.as_posix())}
        (FORMAT PARQUET, CODEC 'snappy');
        """
    )
