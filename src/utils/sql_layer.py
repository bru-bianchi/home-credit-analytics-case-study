"""Reusable helpers for SQL-driven transformed layers such as silver and gold."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path

from .duckdb_utils import (
    execute_sql_script,
    export_table_to_parquet,
    get_table_schema,
    open_duckdb_connection,
    read_sql_file,
    table_exists,
)
from .metadata_store import PIPELINE_EVENTS_TABLE


def normalize_schema_rows(rows):
    """Keep only column name, type and nullability for stable schema comparison."""

    return [(row[0], row[1].upper(), row[2].upper()) for row in rows]


def build_digest(payload) -> str:
    """Return a stable SHA256 digest for any JSON-serializable payload."""

    normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized_payload.encode("utf-8")).hexdigest()


def ensure_runtime_directories(output_dir: Path, artifacts_dir: Path, warehouse_path: Path):
    """Ensure all runtime directories for one transformed layer exist."""

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)


def discover_sql_files(sql_dir: Path):
    """Return the ordered SQL files available for one layer."""

    return sorted(sql_dir.glob("*.sql"))


def extract_target_table_name(sql_path: Path, create_table_pattern, sql_text: str | None = None) -> str:
    """Read a SQL file and infer its target table name."""

    sql_text = sql_text if sql_text is not None else read_sql_file(sql_path)
    match = create_table_pattern.search(sql_text)
    if match is None:
        raise RuntimeError(
            f"sql_target_not_found: expected target CREATE OR REPLACE TABLE in '{sql_path.name}'."
        )
    return match.group("table_name")


def extract_source_dependencies(sql_text: str, target_table_name: str, source_table_pattern, self_schema_name: str):
    """Extract source tables referenced by one SQL file."""

    dependencies = []
    seen = set()
    for match in source_table_pattern.finditer(sql_text):
        schema_name = match.group("schema_name").lower()
        table_name = match.group("table_name")
        if schema_name == self_schema_name and table_name == target_table_name:
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


def topologically_sort_sql_catalog(sql_catalog, dependency_schema_name: str):
    """Order SQL files so self-schema dependencies run first."""

    if not sql_catalog:
        return []

    selected_tables = {item["table_name"] for item in sql_catalog}
    dependents = defaultdict(set)
    in_degree = {item["table_name"]: 0 for item in sql_catalog}
    catalog_by_table = {item["table_name"]: item for item in sql_catalog}

    for item in sql_catalog:
        for dependency in item["dependencies"]:
            if dependency["schema_name"] != dependency_schema_name:
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
            "sql_dependency_cycle_detected: cyclic dependencies found among selected SQL files. "
            f"tables={unresolved}"
        )

    return ordered


def load_sql_catalog(
    *,
    sql_dir: Path,
    create_table_pattern,
    source_table_pattern,
    self_schema_name: str,
    selected_tables=None,
):
    """Load selected SQL files with target table names and dependencies."""

    selected = set(selected_tables or [])
    sql_catalog = []
    for sql_path in discover_sql_files(sql_dir):
        sql_text = read_sql_file(sql_path)
        table_name = extract_target_table_name(sql_path, create_table_pattern, sql_text=sql_text)
        if selected and table_name not in selected:
            continue
        sql_catalog.append(
            {
                "sql_path": sql_path,
                "sql_text": sql_text,
                "table_name": table_name,
                "dependencies": extract_source_dependencies(
                    sql_text, table_name, source_table_pattern, self_schema_name
                ),
                "sql_fingerprint": hashlib.sha256(sql_text.encode("utf-8")).hexdigest(),
            }
        )
    return topologically_sort_sql_catalog(sql_catalog, dependency_schema_name=self_schema_name)


def initialize_sql_warehouse(schema_name: str, warehouse_path: Path, create_metadata_tables):
    """Open and initialize one SQL-driven warehouse schema."""

    connection = open_duckdb_connection(warehouse_path)
    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
    create_metadata_tables(connection)
    return connection


def collect_table_metrics(connection, schema_name: str, table_name: str, *, row_count_key: str, column_count_key: str):
    """Collect row and column counts for one materialized table."""

    row_count = connection.execute(f"SELECT COUNT(*) FROM {schema_name}.{table_name}").fetchone()[0]
    schema_rows = get_table_schema(connection, schema_name, table_name) or []
    normalized_schema = normalize_schema_rows(schema_rows)
    return {
        row_count_key: row_count,
        column_count_key: len(schema_rows),
        "schema": normalized_schema,
    }


def execute_sql_file(connection, schema_name: str, output_dir: Path, sql_path: Path, table_name: str):
    """Execute one SQL script and export the resulting table to parquet."""

    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
    execute_sql_script(connection, sql_path)
    parquet_path = output_dir / f"{table_name}.parquet"
    export_table_to_parquet(connection, schema_name, table_name, parquet_path)
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
            f"source_table_not_found: source table '{schema_name}.{table_name}' does not exist."
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
    """Resolve the current fingerprint of one upstream dependency."""

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
    """Build the current set of source fingerprints for one SQL file."""

    return {
        dependency["dependency_key"]: resolve_dependency_fingerprint(
            connection,
            dependency,
            current_table_fingerprints,
        )
        for dependency in dependencies
    }


def build_table_fingerprint(table_report, *, row_count_key: str, column_count_key: str, version_key: str):
    """Build a fingerprint that represents the current published table."""

    return build_digest(
        {
            "table_name": table_report["table_name"],
            "sql_fingerprint": table_report["sql_fingerprint"],
            "source_fingerprints": table_report["source_fingerprints"],
            "schema": table_report["schema"],
            "row_count": table_report[row_count_key],
            "column_count": table_report[column_count_key],
            "process_version": table_report[version_key],
        }
    )


def can_reuse_cached_table(
    connection,
    *,
    schema_name: str,
    layer_name: str,
    table_name: str,
    parquet_path: Path,
    sql_fingerprint: str,
    source_fingerprints,
    transformation_version: str,
):
    """Return cached metadata when the current inputs fully match a previous run."""

    if not parquet_path.exists():
        return None

    existing_schema = get_table_schema(connection, schema_name, table_name)
    if existing_schema is None:
        return None

    cached_result = load_latest_pipeline_event(connection, layer_name, table_name)
    if cached_result is None:
        return None

    cached_details = cached_result["details"]
    cached_schema = [tuple(row) for row in (cached_details.get("schema") or [])]

    if cached_result["process_version"] != transformation_version:
        return None
    if cached_details.get("sql_fingerprint") != sql_fingerprint:
        return None
    if cached_details.get("source_fingerprints") != source_fingerprints:
        return None
    if normalize_schema_rows(existing_schema) != cached_schema:
        return None

    return {
        "row_count": cached_result["row_count"],
        "column_count": cached_result["column_count"],
        "schema": cached_schema,
        "table_fingerprint": cached_details.get("table_fingerprint"),
    }


def write_execution_report(run_report, artifacts_dir: Path, report_file_name: str, error_prefix: str):
    """Persist the execution report and raise if any table failed."""

    report_path = artifacts_dir / report_file_name
    report_path.write_text(json.dumps(run_report, indent=2), encoding="utf-8")
    if run_report["table_count_failed"] > 0:
        raise RuntimeError(
            f"{error_prefix}: one or more tables failed to load. "
            f"See '{report_path}' and metadados.pipeline_events for details."
        )
    return run_report


def build_sql_layer(
    selected_tables=None,
    *,
    layer_name: str,
    schema_name: str,
    sql_dir: Path,
    output_dir: Path,
    artifacts_dir: Path,
    warehouse_path: Path,
    transformation_version: str,
    create_table_pattern,
    source_table_pattern,
    create_metadata_tables,
    initialize_run_report,
    append_table_report,
    finalize_run_report,
    persist_run_report,
):
    """Build one SQL-driven layer from versioned SQL files and export them to parquet."""

    row_count_key = f"{layer_name}_row_count"
    column_count_key = f"{layer_name}_column_count"
    version_key = f"{layer_name}_transformation_version"

    ensure_runtime_directories(output_dir, artifacts_dir, warehouse_path)
    sql_catalog = load_sql_catalog(
        sql_dir=sql_dir,
        create_table_pattern=create_table_pattern,
        source_table_pattern=source_table_pattern,
        self_schema_name=schema_name,
        selected_tables=selected_tables,
    )
    run_report = initialize_run_report([item["table_name"] for item in sql_catalog])
    connection = None
    current_table_fingerprints = {}

    try:
        connection = initialize_sql_warehouse(schema_name, warehouse_path, create_metadata_tables)

        for item in sql_catalog:
            table_name = item["table_name"]
            table_report = append_table_report(
                run_report=run_report,
                table_name=table_name,
                sql_file_name=item["sql_path"].name,
                parquet_path=output_dir / f"{table_name}.parquet",
                transformation_version=transformation_version,
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
                    connection,
                    schema_name=schema_name,
                    layer_name=layer_name,
                    table_name=table_name,
                    parquet_path=Path(table_report["parquet_path"]),
                    sql_fingerprint=item["sql_fingerprint"],
                    source_fingerprints=table_report["source_fingerprints"],
                    transformation_version=transformation_version,
                )
                if cached_result is not None:
                    table_report["used_cached_transformation"] = True
                    table_report[row_count_key] = cached_result["row_count"]
                    table_report[column_count_key] = cached_result["column_count"]
                    table_report["schema"] = cached_result["schema"]
                    table_report["table_fingerprint"] = (
                        cached_result["table_fingerprint"]
                        or build_table_fingerprint(
                            table_report,
                            row_count_key=row_count_key,
                            column_count_key=column_count_key,
                            version_key=version_key,
                        )
                    )
                    table_report["table_status"] = "skipped_cached_transformation"
                    current_table_fingerprints[f"{schema_name}.{table_name}"] = table_report["table_fingerprint"]
                    continue

                parquet_path = execute_sql_file(connection, schema_name, output_dir, item["sql_path"], table_name)
                table_report["parquet_path"] = str(parquet_path)
                table_report.update(
                    collect_table_metrics(
                        connection,
                        schema_name,
                        table_name,
                        row_count_key=row_count_key,
                        column_count_key=column_count_key,
                    )
                )
                table_report["table_fingerprint"] = build_table_fingerprint(
                    table_report,
                    row_count_key=row_count_key,
                    column_count_key=column_count_key,
                    version_key=version_key,
                )
                table_report["table_status"] = "success"
                current_table_fingerprints[f"{schema_name}.{table_name}"] = table_report["table_fingerprint"]
            except Exception as exc:
                table_report["table_status"] = "failed"
                table_report["error_message"] = f"{type(exc).__name__}: {exc}"

        from datetime import datetime

        finished_at_utc = datetime.utcnow().replace(microsecond=0)
        finalize_run_report(run_report)
        persist_run_report(connection, run_report, finished_at_utc)
    finally:
        if connection is not None:
            connection.close()

    return write_execution_report(
        run_report,
        artifacts_dir,
        f"{layer_name}_transformation_report.json",
        f"{layer_name}_transformation_failed",
    )
