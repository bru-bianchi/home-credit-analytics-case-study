"""DuckDB access helpers for the Streamlit dashboard."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WAREHOUSE_PATH = PROJECT_ROOT / "data" / "warehouse" / "credit_risk.duckdb"
DEFAULT_MOTHERDUCK_DATABASE = "credit_risk"
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


def _get_secret(name: str) -> str | None:
    """Return a Streamlit secret or environment variable without requiring secrets locally."""

    for key in (name, name.lower()):
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None

        value = value or os.getenv(key)
        if value:
            return str(value).strip()

    return None


def _motherduck_database() -> str:
    return _get_secret("MOTHERDUCK_DATABASE") or DEFAULT_MOTHERDUCK_DATABASE


def _motherduck_token() -> str | None:
    return _get_secret("MOTHERDUCK_TOKEN")


def _motherduck_token_fingerprint() -> str:
    token = _motherduck_token()
    if not token:
        return ""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _connect_motherduck(database_name: str):
    """Open a MotherDuck connection when a token is available in the environment."""

    token = _motherduck_token()
    if not token:
        return None

    os.environ["MOTHERDUCK_TOKEN"] = token
    os.environ["motherduck_token"] = token
    return duckdb.connect(f"md:{database_name}")


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
def _get_connection_cached(warehouse_path: str, motherduck_database: str, token_fingerprint: str):
    """Open a DuckDB connection for dashboard queries.

    The dashboard reads from MotherDuck when MOTHERDUCK_TOKEN is configured.
    Without that token, it reads the local warehouse and falls back to Gold
    Parquet outputs when the local file is unavailable or locked.
    """

    if token_fingerprint:
        return _connect_motherduck(motherduck_database)

    try:
        return duckdb.connect(str(Path(warehouse_path).expanduser()), read_only=True)
    except duckdb.IOException:
        return _connect_gold_parquet_views()


def get_connection(warehouse_path: str):
    """Resolve the active data source and return a cached connection for it."""

    return _get_connection_cached(
        str(Path(warehouse_path).expanduser()),
        _motherduck_database(),
        _motherduck_token_fingerprint(),
    )


def describe_data_source(warehouse_path: str) -> str:
    """Return a human-readable data source description for the dashboard."""

    if _motherduck_token():
        return f"Fonte primaria: MotherDuck (`md:{_motherduck_database()}`)."

    return (
        "Fonte primaria local: warehouse DuckDB em "
        f"`{Path(warehouse_path).expanduser()}`. Fallback: Parquets em `data/gold`."
    )


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
