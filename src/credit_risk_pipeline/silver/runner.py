"""Execution layer for bronze-to-silver SQL transformations and parquet export."""

from __future__ import annotations

import re
from datetime import datetime

from utils import build_sql_layer

from .config import ARTIFACTS_DIR, SILVER_DIR, SILVER_SQL_DIR, SILVER_TRANSFORMATION_VERSION, WAREHOUSE_PATH
from .create_metadata import (
    append_table_report,
    create_metadata_tables,
    finalize_run_report,
    initialize_run_report,
    persist_run_report,
)


CREATE_TABLE_PATTERN = re.compile(
    r"CREATE\s+OR\s+REPLACE\s+TABLE\s+silver\.(?P<table_name>[A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
SOURCE_TABLE_PATTERN = re.compile(
    r"\b(?P<schema_name>bronze|silver)\.(?P<table_name>[A-Za-z_][A-Za-z0-9_]*)\b",
    re.IGNORECASE,
)


def initialize_silver_run_report(table_names):
    """Create the run report structure for the current silver execution."""

    started_at_utc = datetime.utcnow().replace(microsecond=0)
    return initialize_run_report(
        started_at_utc=started_at_utc,
        warehouse_path=WAREHOUSE_PATH,
        silver_directory=SILVER_DIR,
        sql_directory=SILVER_SQL_DIR,
        table_names=table_names,
    )


def build_silver_layer(selected_tables=None):
    """Build silver tables from versioned DuckDB SQL and export them to parquet."""

    return build_sql_layer(
        selected_tables,
        layer_name="silver",
        schema_name="silver",
        sql_dir=SILVER_SQL_DIR,
        output_dir=SILVER_DIR,
        artifacts_dir=ARTIFACTS_DIR,
        warehouse_path=WAREHOUSE_PATH,
        transformation_version=SILVER_TRANSFORMATION_VERSION,
        create_table_pattern=CREATE_TABLE_PATTERN,
        source_table_pattern=SOURCE_TABLE_PATTERN,
        create_metadata_tables=create_metadata_tables,
        initialize_run_report=initialize_silver_run_report,
        append_table_report=append_table_report,
        finalize_run_report=finalize_run_report,
        persist_run_report=persist_run_report,
    )
