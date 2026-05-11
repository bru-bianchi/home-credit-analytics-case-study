"""Execution layer for bronze-to-silver SQL transformations and parquet export."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from utils import (
    PIPELINE_EVENTS_TABLE,
    close_duckdb_connection,
    execute_sql_script,
    export_table_to_parquet,
    get_table_schema,
    open_duckdb_connection,
    read_sql_file,
    table_exists,
)

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


def normalize_schema_rows(rows):
    """Keep only column name, type and nullability for stable schema comparison."""

    return [(row[0], row[1].upper(), row[2].upper()) for row in rows]


def build_digest(payload) -> str:
    """Return a stable SHA256 digest for any JSON-serializable payload."""

    normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()


def ensure_silver_runtime_directories():
    """Ensure silver output directories exist before execution."""

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)


def discover_silver_sql_files():
    """Return the ordered silver SQL files available in the repository."""

    return sorted(SILVER_SQL_DIR.glob("*.sql"))


def extract_target_table_name(sql_path: Path, sql_text: str | None = None) -> str:
    """Read a silver SQL file and infer the target silver table name."""

    sql_text = sql_text if sql_text is not None else read_sql_file(sql_path)
    match = CREATE_TABLE_PATTERN.search(sql_text)
    if match is None:
        raise RuntimeError(
            f"silver_sql_target_not_found: expected CREATE OR REPLACE TABLE silver.<table> in '{sql_path.name}'."
        )
    return match.group("table_name")


def extract_source_dependencies(sql_text: str, target_table_name: str):
    """Extract bronze/silver source tables referenced by one silver SQL file."""

    dependencies = []
    seen = set()
    for match in SOURCE_TABLE_PATTERN.finditer(sql_text):
        schema_name = match.group("schema_name").lower()
        table_name = match.group("table_name")
        if schema_name == "silver" and table_name == target_table_name:
            continue
        dependency_key = f"{schema_name}.{table_name}"
        if dependency_key in seen:
            continue
        dependencies.append(
            {
                "schema_name": schema_name,
                "table_name": table_name,
                "dependency_key": dependency_key,
            }
        )
        seen.add(dependency_key)
    return dependencies


def load_silver_sql_catalog(selected_tables=None):
    """Load selected silver SQL files with target table names and dependencies."""

    selected = set(selected_tables or [])
    sql_catalog = []
    for sql_path in discover_silver_sql_files():
        sql_text = read_sql_file(sql_path)
        table_name = extract_target_table_name(sql_path, sql_text=sql_text)
        if selected and table_name not in selected:
            continue
        sql_catalog.append(
            {
                "sql_path": sql_path,
                "sql_text": sql_text,
                "table_name": table_name,
                "dependencies": extract_source_dependencies(sql_text, table_name),
                "sql_fingerprint": hashlib.sha256(sql_text.encode("utf-8")).hexdigest(),
            }
        )
    return topologically_sort_silver_sql_catalog(sql_catalog)


def topologically_sort_silver_sql_catalog(sql_catalog):
    """Order selected silver SQL files so silver-on-silver dependencies run first."""

    if not sql_catalog:
        return []

    selected_tables = {item["table_name"] for item in sql_catalog}
    dependents = defaultdict(set)
    in_degree = {item["table_name"]: 0 for item in sql_catalog}
    catalog_by_table = {item["table_name"]: item for item in sql_catalog}

    for item in sql_catalog:
        for dependency in item["dependencies"]:
            if dependency["schema_name"] != "silver":
                continue
            dependency_table = dependency["table_name"]
            if dependency_table not in selected_tables:
                continue
            dependents[dependency_table].add(item["table_name"])
            in_degree[item["table_name"]] += 1

    queue = deque(sorted(table_name for table_name, degree in in_degree.items() if degree == 0))
    ordered = []
    while queue:
        table_name = queue.popleft()
        ordered.append(catalog_by_table[table_name])
        for dependent_table in sorted(dependents[table_name]):
            in_degree[dependent_table] -= 1
            if in_degree[dependent_table] == 0:
                queue.append(dependent_table)

    if len(ordered) != len(sql_catalog):
        unresolved = sorted(table_name for table_name, degree in in_degree.items() if degree > 0)
        raise RuntimeError(
            "silver_dependency_cycle_detected: cyclic dependencies found among selected silver SQL files. "
            f"tables={unresolved}"
        )

    return ordered


def initialize_silver_warehouse():
    """Open and initialize the silver warehouse structures."""

    connection = open_duckdb_connection(WAREHOUSE_PATH)
    connection.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    create_metadata_tables(connection)
    return connection


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


def collect_silver_table_metrics(connection, table_name):
    """Collect row and column counts for a silver table already loaded in the warehouse."""

    row_count = connection.execute(f"SELECT COUNT(*) FROM silver.{table_name}").fetchone()[0]
    schema_rows = get_table_schema(connection, "silver", table_name) or []
    normalized_schema = normalize_schema_rows(schema_rows)
    return {
        "silver_row_count": row_count,
        "silver_column_count": len(schema_rows),
        "schema": normalized_schema,
    }


def execute_silver_sql_file(connection, sql_path: Path, table_name: str):
    """Execute one silver SQL script and export the resulting table to parquet."""

    connection.execute("CREATE SCHEMA IF NOT EXISTS silver;")
    execute_sql_script(connection, sql_path)
    parquet_path = SILVER_DIR / f"{table_name}.parquet"
    export_table_to_parquet(connection, "silver", table_name, parquet_path)
    return parquet_path


def load_latest_pipeline_event(connection, layer: str, table_name: str):
    """Load the latest successful pipeline metadata for one transformed table."""

    if not table_exists(connection, "metadados", "pipeline_events"):
        return None

    row = connection.execute(
        f"""
        SELECT artifact_path, process_version, row_count, column_count, details_json
        FROM {PIPELINE_EVENTS_TABLE}
        WHERE layer = ?
          AND entity_type = 'table'
          AND entity_name = ?
          AND status IN ('success', 'skipped_cached_transformation')
        ORDER BY rowid DESC
        LIMIT 1
        """,
        [layer, table_name],
    ).fetchone()
    if row is None:
        return None

    details = json.loads(row[4]) if row[4] else {}
    return {
        "artifact_path": row[0],
        "process_version": row[1],
        "row_count": row[2],
        "column_count": row[3],
        "details": details,
    }


def build_source_fingerprint_from_metadata(schema_name: str, table_name: str, event):
    """Build a stable dependency fingerprint from persisted table metadata."""

    details = event["details"]
    schema = details.get("schema") or []
    payload = {
        "schema_name": schema_name,
        "table_name": table_name,
        "process_version": event["process_version"],
        "row_count": event["row_count"],
        "column_count": event["column_count"],
        "artifact_path": event["artifact_path"],
        "schema": schema,
        "table_fingerprint": details.get("table_fingerprint"),
        "raw_file_fingerprint": details.get("raw_file_fingerprint"),
        "source_fingerprints": details.get("source_fingerprints"),
    }
    return build_digest(payload)


def build_source_fingerprint_from_physical_table(connection, schema_name: str, table_name: str):
    """Fallback fingerprint when metadata is not available but the table exists."""

    schema_rows = get_table_schema(connection, schema_name, table_name)
    if schema_rows is None:
        raise RuntimeError(
            f"silver_source_table_not_found: source table '{schema_name}.{table_name}' does not exist."
        )

    normalized_schema = normalize_schema_rows(schema_rows)
    row_count = connection.execute(
        f"SELECT COUNT(*) FROM {schema_name}.{table_name}"
    ).fetchone()[0]
    return build_digest(
        {
            "schema_name": schema_name,
            "table_name": table_name,
            "row_count": row_count,
            "schema": normalized_schema,
            "fallback": True,
        }
    )


def resolve_dependency_fingerprint(connection, dependency, current_table_fingerprints):
    """Resolve the current fingerprint of one bronze/silver dependency."""

    dependency_key = dependency["dependency_key"]
    if dependency_key in current_table_fingerprints:
        return current_table_fingerprints[dependency_key]

    event = load_latest_pipeline_event(
        connection,
        layer=dependency["schema_name"],
        table_name=dependency["table_name"],
    )
    if event is not None:
        return build_source_fingerprint_from_metadata(
            dependency["schema_name"],
            dependency["table_name"],
            event,
        )

    return build_source_fingerprint_from_physical_table(
        connection,
        dependency["schema_name"],
        dependency["table_name"],
    )


def build_dependency_fingerprints(connection, dependencies, current_table_fingerprints):
    """Build the current set of source fingerprints for one silver SQL file."""

    return {
        dependency["dependency_key"]: resolve_dependency_fingerprint(
            connection,
            dependency,
            current_table_fingerprints,
        )
        for dependency in dependencies
    }


def build_table_fingerprint(table_report):
    """Build a fingerprint that represents the current published silver table."""

    return build_digest(
        {
            "table_name": table_report["table_name"],
            "sql_fingerprint": table_report["sql_fingerprint"],
            "source_fingerprints": table_report["source_fingerprints"],
            "schema": table_report["schema"],
            "row_count": table_report["silver_row_count"],
            "column_count": table_report["silver_column_count"],
            "process_version": table_report["silver_transformation_version"],
        }
    )


def can_reuse_cached_table(
    connection,
    table_name: str,
    parquet_path: Path,
    sql_fingerprint: str,
    source_fingerprints,
    silver_transformation_version: str,
):
    """Return cached silver metadata when the current inputs fully match a previous run."""

    if not parquet_path.exists():
        return None

    existing_schema = get_table_schema(connection, "silver", table_name)
    if existing_schema is None:
        return None

    cached_result = load_latest_pipeline_event(connection, "silver", table_name)
    if cached_result is None:
        return None

    cached_details = cached_result["details"]
    cached_schema = [tuple(row) for row in (cached_details.get("schema") or [])]

    if cached_result["process_version"] != silver_transformation_version:
        return None
    if cached_details.get("sql_fingerprint") != sql_fingerprint:
        return None
    if cached_details.get("source_fingerprints") != source_fingerprints:
        return None
    if normalize_schema_rows(existing_schema) != cached_schema:
        return None

    return {
        "silver_row_count": cached_result["row_count"],
        "silver_column_count": cached_result["column_count"],
        "schema": cached_schema,
        "table_fingerprint": cached_details.get("table_fingerprint"),
    }


def write_silver_execution_report(run_report):
    """Persist the silver execution report and raise if any table failed."""

    report_path = ARTIFACTS_DIR / "silver_transformation_report.json"
    report_path.write_text(json.dumps(run_report, indent=2), encoding="utf-8")
    if run_report["table_count_failed"] > 0:
        raise RuntimeError(
            "silver_transformation_failed: one or more silver tables failed to load. "
            f"See '{report_path}' and metadados.pipeline_events for details."
        )
    return run_report


def build_silver_layer(selected_tables=None):
    """Build silver tables from versioned DuckDB SQL and export them to parquet."""

    ensure_silver_runtime_directories()
    sql_catalog = load_silver_sql_catalog(selected_tables)
    run_report = initialize_silver_run_report([item["table_name"] for item in sql_catalog])
    connection = None
    current_table_fingerprints = {}

    try:
        connection = initialize_silver_warehouse()

        for item in sql_catalog:
            table_name = item["table_name"]
            table_report = append_table_report(
                run_report=run_report,
                table_name=table_name,
                sql_file_name=item["sql_path"].name,
                parquet_path=SILVER_DIR / f"{table_name}.parquet",
                silver_transformation_version=SILVER_TRANSFORMATION_VERSION,
            )
            table_report["sql_fingerprint"] = item["sql_fingerprint"]
            table_report["source_dependencies"] = [
                dependency["dependency_key"] for dependency in item["dependencies"]
            ]

            try:
                table_report["source_fingerprints"] = build_dependency_fingerprints(
                    connection,
                    item["dependencies"],
                    current_table_fingerprints,
                )
                cached_result = can_reuse_cached_table(
                    connection=connection,
                    table_name=table_name,
                    parquet_path=Path(table_report["parquet_path"]),
                    sql_fingerprint=item["sql_fingerprint"],
                    source_fingerprints=table_report["source_fingerprints"],
                    silver_transformation_version=SILVER_TRANSFORMATION_VERSION,
                )
                if cached_result is not None:
                    table_report["used_cached_transformation"] = True
                    table_report["silver_row_count"] = cached_result["silver_row_count"]
                    table_report["silver_column_count"] = cached_result["silver_column_count"]
                    table_report["schema"] = cached_result["schema"]
                    table_report["table_fingerprint"] = (
                        cached_result["table_fingerprint"] or build_table_fingerprint(table_report)
                    )
                    table_report["table_status"] = "skipped_cached_transformation"
                    current_table_fingerprints[f"silver.{table_name}"] = table_report["table_fingerprint"]
                    continue

                parquet_path = execute_silver_sql_file(connection, item["sql_path"], table_name)
                table_report["parquet_path"] = str(parquet_path)
                table_report.update(collect_silver_table_metrics(connection, table_name))
                table_report["table_fingerprint"] = build_table_fingerprint(table_report)
                table_report["table_status"] = "success"
                current_table_fingerprints[f"silver.{table_name}"] = table_report["table_fingerprint"]
            except Exception as exc:
                table_report["table_status"] = "failed"
                table_report["error_message"] = f"{type(exc).__name__}: {exc}"

        finished_at_utc = datetime.utcnow().replace(microsecond=0)
        finalize_run_report(run_report)
        persist_run_report(connection, run_report, finished_at_utc)
    finally:
        close_duckdb_connection(connection)

    return write_silver_execution_report(run_report)
