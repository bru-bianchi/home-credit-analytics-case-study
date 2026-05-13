"""DuckDB access helpers for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"
GOLD_PARQUET_DIR = PROJECT_ROOT / "data" / "gold"
GOLD_TABLES = (
    "fact_credit_risk",
    "dim_requester",
    "dim_contract",
    "dim_risk_segment",
    "ref_band_rules",
)


def _quote_path(path: Path) -> str:
    return str(path).replace("'", "''")


def _connect_gold_parquet_views():
    """Create an in-memory connection with Gold Parquet files exposed as views."""

    connection = duckdb.connect()
    connection.execute("CREATE SCHEMA IF NOT EXISTS gold")

    for table_name in GOLD_TABLES:
        parquet_path = GOLD_PARQUET_DIR / f"{table_name}.parquet"
        if parquet_path.exists():
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW gold.{table_name} AS
                SELECT * FROM read_parquet('{_quote_path(parquet_path)}')
                """
            )

    return connection


@st.cache_resource(show_spinner=False)
def get_connection(warehouse_path: str):
    """Open a DuckDB connection for dashboard queries.

    The primary source is the local warehouse. If it is locked by another DuckDB
    process, the app falls back to the Gold Parquet outputs.
    """

    try:
        return duckdb.connect(str(Path(warehouse_path).expanduser()), read_only=True)
    except duckdb.IOException:
        return _connect_gold_parquet_views()


def query_df(sql: str, warehouse_path: str, params: list | None = None) -> pd.DataFrame:
    """Execute a SQL query and return a dataframe."""

    connection = get_connection(warehouse_path)
    return connection.execute(sql, params or []).fetchdf()


def list_gold_tables(warehouse_path: str) -> pd.DataFrame:
    """Return available Gold tables in the warehouse."""

    return query_df(
        """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'gold'
        ORDER BY table_name
        """,
        warehouse_path,
    )


def table_exists(schema_name: str, table_name: str, warehouse_path: str) -> bool:
    """Check whether a table exists in the connected DuckDB warehouse."""

    result = query_df(
        """
        SELECT COUNT(*) AS table_count
        FROM information_schema.tables
        WHERE table_schema = ?
          AND table_name = ?
        """,
        warehouse_path,
        [schema_name, table_name],
    )
    return bool(result.loc[0, "table_count"])


def table_columns(schema_name: str, table_name: str, warehouse_path: str) -> list[str]:
    """Return column names for a table."""

    result = query_df(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = ?
          AND table_name = ?
        ORDER BY ordinal_position
        """,
        warehouse_path,
        [schema_name, table_name],
    )
    return result["column_name"].tolist()
