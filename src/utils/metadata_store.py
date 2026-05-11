"""Shared metadata persistence helpers for pipeline observability tables."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any


PIPELINE_EVENTS_TABLE = "metadados.pipeline_events"
RAW_VALIDATION_EVENTS_TABLE = "metadados.raw_validation_events"


def _normalize_timestamp(value: Any) -> datetime | None:
    """Return a Python datetime for database insertion when a value is present."""

    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", ""))
    raise TypeError(f"Unsupported timestamp value: {value!r}")


def _derive_event_date(value: Any) -> date | None:
    """Derive a calendar date from a timestamp-like value."""

    timestamp = _normalize_timestamp(value)
    if timestamp is None:
        return None
    return timestamp.date()


def _json_payload(details: dict[str, Any] | None) -> str | None:
    """Serialize free-form event metadata only when provided."""

    if details is None:
        return None
    return json.dumps(details)


def create_pipeline_events_table(connection) -> None:
    """Create the canonical metadata table for transformed pipeline layers."""

    connection.execute("CREATE SCHEMA IF NOT EXISTS metadados;")
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {PIPELINE_EVENTS_TABLE} (
            run_id VARCHAR,
            event_ts_utc TIMESTAMP,
            event_date DATE,
            layer VARCHAR,
            entity_type VARCHAR,
            entity_name VARCHAR,
            status VARCHAR,
            started_at_utc TIMESTAMP,
            finished_at_utc TIMESTAMP,
            warehouse_path VARCHAR,
            output_directory VARCHAR,
            source_name VARCHAR,
            artifact_path VARCHAR,
            process_version VARCHAR,
            row_count BIGINT,
            column_count INTEGER,
            error_message VARCHAR,
            used_cached_result BOOLEAN,
            details_json VARCHAR
        );
        """
    )


def create_raw_validation_events_table(connection) -> None:
    """Create the raw-validation metadata table kept separate from transformed layers."""

    connection.execute("CREATE SCHEMA IF NOT EXISTS metadados;")
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RAW_VALIDATION_EVENTS_TABLE} (
            run_id VARCHAR,
            event_ts_utc TIMESTAMP,
            event_date DATE,
            layer VARCHAR,
            entity_type VARCHAR,
            entity_name VARCHAR,
            status VARCHAR,
            started_at_utc TIMESTAMP,
            finished_at_utc TIMESTAMP,
            warehouse_path VARCHAR,
            output_directory VARCHAR,
            source_name VARCHAR,
            artifact_path VARCHAR,
            file_fingerprint VARCHAR,
            process_version VARCHAR,
            row_count BIGINT,
            column_count INTEGER,
            error_message VARCHAR,
            used_cached_result BOOLEAN,
            details_json VARCHAR
        );
        """
    )


def insert_pipeline_event(
    connection,
    *,
    run_id: str,
    event_ts_utc: Any,
    layer: str,
    entity_type: str,
    entity_name: str,
    status: str,
    started_at_utc: Any = None,
    finished_at_utc: Any = None,
    warehouse_path: str | None = None,
    output_directory: str | None = None,
    source_name: str | None = None,
    artifact_path: str | None = None,
    process_version: str | None = None,
    row_count: int | None = None,
    column_count: int | None = None,
    error_message: str | None = None,
    used_cached_result: bool | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Insert one canonical metadata event for bronze/silver/gold layers."""

    normalized_event_ts = _normalize_timestamp(event_ts_utc)
    connection.execute(
        f"""
        INSERT INTO {PIPELINE_EVENTS_TABLE} (
            run_id,
            event_ts_utc,
            event_date,
            layer,
            entity_type,
            entity_name,
            status,
            started_at_utc,
            finished_at_utc,
            warehouse_path,
            output_directory,
            source_name,
            artifact_path,
            process_version,
            row_count,
            column_count,
            error_message,
            used_cached_result,
            details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            normalized_event_ts,
            _derive_event_date(normalized_event_ts),
            layer,
            entity_type,
            entity_name,
            status,
            _normalize_timestamp(started_at_utc),
            _normalize_timestamp(finished_at_utc),
            warehouse_path,
            output_directory,
            source_name,
            artifact_path,
            process_version,
            row_count,
            column_count,
            error_message,
            used_cached_result,
            _json_payload(details),
        ],
    )


def insert_raw_validation_event(
    connection,
    *,
    run_id: str,
    event_ts_utc: Any,
    entity_type: str,
    entity_name: str,
    status: str,
    started_at_utc: Any = None,
    finished_at_utc: Any = None,
    warehouse_path: str | None = None,
    output_directory: str | None = None,
    source_name: str | None = None,
    artifact_path: str | None = None,
    file_fingerprint: str | None = None,
    process_version: str | None = None,
    row_count: int | None = None,
    column_count: int | None = None,
    error_message: str | None = None,
    used_cached_result: bool | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Insert one raw validation event in the dedicated raw metadata table."""

    normalized_event_ts = _normalize_timestamp(event_ts_utc)
    connection.execute(
        f"""
        INSERT INTO {RAW_VALIDATION_EVENTS_TABLE} (
            run_id,
            event_ts_utc,
            event_date,
            layer,
            entity_type,
            entity_name,
            status,
            started_at_utc,
            finished_at_utc,
            warehouse_path,
            output_directory,
            source_name,
            artifact_path,
            file_fingerprint,
            process_version,
            row_count,
            column_count,
            error_message,
            used_cached_result,
            details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            run_id,
            normalized_event_ts,
            _derive_event_date(normalized_event_ts),
            "raw",
            entity_type,
            entity_name,
            status,
            _normalize_timestamp(started_at_utc),
            _normalize_timestamp(finished_at_utc),
            warehouse_path,
            output_directory,
            source_name,
            artifact_path,
            file_fingerprint,
            process_version,
            row_count,
            column_count,
            error_message,
            used_cached_result,
            _json_payload(details),
        ],
    )
