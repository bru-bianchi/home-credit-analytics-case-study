"""Shared utility helpers used across analytical pipeline layers."""

from .duckdb_utils import (
    close_duckdb_connection,
    execute_sql_script,
    export_table_to_parquet,
    get_table_schema,
    open_duckdb_connection,
    quote_identifier,
    quote_string,
    read_csv_relation,
    read_sql_file,
    table_exists,
)
from .metadata_store import (
    PIPELINE_EVENTS_TABLE,
    RAW_VALIDATION_EVENTS_TABLE,
    create_pipeline_events_table,
    create_raw_validation_events_table,
    insert_pipeline_event,
    insert_raw_validation_event,
)
from .naming_utils import snake_case

__all__ = [
    "PIPELINE_EVENTS_TABLE",
    "RAW_VALIDATION_EVENTS_TABLE",
    "close_duckdb_connection",
    "create_pipeline_events_table",
    "create_raw_validation_events_table",
    "execute_sql_script",
    "export_table_to_parquet",
    "get_table_schema",
    "insert_pipeline_event",
    "insert_raw_validation_event",
    "open_duckdb_connection",
    "quote_identifier",
    "quote_string",
    "read_csv_relation",
    "read_sql_file",
    "snake_case",
    "table_exists",
]
