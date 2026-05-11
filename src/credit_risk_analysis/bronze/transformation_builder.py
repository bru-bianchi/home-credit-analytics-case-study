"""Transformation building and rule inference for the bronze layer."""

from .schema_mapping import (
    REFERENCE_SCHEMA_PATH,
    evaluate_schema,
    load_sentinel_mapping,
    resolve_column_mapping,
)
from .config import (
    BOOLEAN_LITERALS,
    BRONZE_COLUMN_MAPPING_PATH,
    BRONZE_DIR,
    BRONZE_SENTINEL_MAPPING_PATH,
    BRONZE_TRANSFORMATION_VERSION,
    BRONZE_SCHEMA_MAPPING_PATH,
    RAW_DIR,
)
from utils.duckdb_utils import quote_identifier, read_csv_relation


def resolve_raw_csv_path(table):
    """Resolve the raw CSV path for one configured table."""

    csv_path = RAW_DIR / table["file_name"]
    if not csv_path.exists():
        raise FileNotFoundError(f"missing_raw_file: expected '{csv_path}'.")
    return csv_path


def read_raw_file_fingerprint(csv_path):
    """Build a stable fingerprint for the current raw file contents identity."""

    stat = csv_path.stat()
    return f"{csv_path}|{stat.st_size}|{stat.st_mtime_ns}"


def read_dependency_file_fingerprint(file_path):
    """Build a stable fingerprint for a transformation dependency file."""

    stat = file_path.stat()
    return f"{file_path}|{stat.st_size}|{stat.st_mtime_ns}"


def build_bronze_transformation_signature():
    """Build a lightweight cache signature for the current bronze transformation setup."""

    dependency_fingerprints = [
        read_dependency_file_fingerprint(BRONZE_COLUMN_MAPPING_PATH),
        read_dependency_file_fingerprint(BRONZE_SCHEMA_MAPPING_PATH),
        read_dependency_file_fingerprint(BRONZE_SENTINEL_MAPPING_PATH),
        read_dependency_file_fingerprint(REFERENCE_SCHEMA_PATH),
    ]
    return "|".join([BRONZE_TRANSFORMATION_VERSION, *dependency_fingerprints])


def read_raw_columns(profile_connection, csv_path):
    """Read the raw source columns and inferred types for one CSV."""

    return profile_connection.execute(
        f"DESCRIBE SELECT * FROM {read_csv_relation(csv_path)}"
    ).fetchall()


def read_raw_row_count(profile_connection, csv_path):
    """Read the number of rows currently present in the raw CSV."""

    return profile_connection.execute(
        f"SELECT COUNT(*) FROM {read_csv_relation(csv_path)}"
    ).fetchone()[0]


def detect_boolean_columns(profile_connection, csv_path, raw_columns):
    """Detect columns whose non-null domain is restricted to accepted boolean literals."""

    candidates = set()
    relation_sql = read_csv_relation(csv_path)

    for column_name, _column_type, *_ in raw_columns:
        distinct_values = profile_connection.execute(
            f"""
            SELECT DISTINCT lower(trim(CAST({quote_identifier(column_name)} AS VARCHAR))) AS value
            FROM {relation_sql}
            WHERE {quote_identifier(column_name)} IS NOT NULL
            ORDER BY 1
            """
        ).fetchall()

        normalized_values = {value[0] for value in distinct_values if value[0] is not None}
        if normalized_values and normalized_values.issubset(BOOLEAN_LITERALS):
            candidates.add(column_name)

    return candidates


def detect_sentinel_columns(profile_connection, table, csv_path, raw_columns):
    """Detect columns with explicit sentinel replacement rules and active matches in raw."""

    sentinel_columns = {}
    relation_sql = read_csv_relation(csv_path)
    sentinel_mapping = load_sentinel_mapping()
    file_name = table["file_name"]

    for column_name, _column_type, *_ in raw_columns:
        sentinel_rule = sentinel_mapping.get((file_name, column_name))
        if sentinel_rule is None:
            continue

        sentinel_count = profile_connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {relation_sql}
            WHERE {quote_identifier(column_name)} = {sentinel_rule['sentinel_sql']}
            """
        ).fetchone()[0]

        if sentinel_count:
            sentinel_columns[column_name] = sentinel_rule

    return sentinel_columns


def validate_non_nullable_source_columns(profile_connection, csv_path, column_rules):
    """Ensure columns marked as non-nullable do not contain nulls in raw data."""

    relation_sql = read_csv_relation(csv_path)
    errors = []

    for rule in column_rules:
        if rule["bronze_nullable"] != "NO":
            continue

        source_column = rule["source_column"]
        null_count = profile_connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {relation_sql}
            WHERE {quote_identifier(source_column)} IS NULL
            """
        ).fetchone()[0]
        if null_count:
            errors.append(
                f"non_nullable_column_has_nulls:{source_column}:null_count={null_count}"
            )

    if errors:
        raise RuntimeError("bronze_non_nullable_validation_failed: " + "; ".join(errors))


def build_transformation_expression(column_name, boolean_columns, sentinel_columns, mapping):
    """Build the SQL expression and rules used to transform one source column."""

    source_identifier = quote_identifier(column_name)

    if column_name in boolean_columns:
        expression = (
            f"CASE "
            f"WHEN {source_identifier} IS NULL THEN NULL "
            f"WHEN lower(trim(CAST({source_identifier} AS VARCHAR))) IN ('1', 'true', 'y', 'yes') THEN TRUE "
            f"WHEN lower(trim(CAST({source_identifier} AS VARCHAR))) IN ('0', 'false', 'n', 'no') THEN FALSE "
            f"ELSE NULL "
            f"END"
        )
        rules = ["boolean_normalization"]
    elif column_name in sentinel_columns:
        sentinel_rule = sentinel_columns[column_name]
        expression = (
            f"CASE "
            f"WHEN {source_identifier} = {sentinel_rule['sentinel_sql']} "
            f"THEN {sentinel_rule['replacement_sql']} "
            f"ELSE {source_identifier} "
            f"END"
        )
        rules = [
            "sentinel_replacement",
            f"replace_{sentinel_rule['sentinel_sql']}_with_{sentinel_rule['replacement_sql'].lower()}",
        ]
    else:
        expression = source_identifier
        rules = []

    if mapping["bronze_type"]:
        expression = f"CAST(({expression}) AS {mapping['bronze_type']})"
        rules = rules + [f"cast_to_{mapping['bronze_type'].lower()}"]

    if mapping["mapping_source"] == "manual_override":
        rules = ["manual_column_rename"] + rules

    return expression, rules


def build_column_rule(column_name, mapping, rules):
    """Build the rule metadata returned in the bronze plan for one column."""

    return {
        "source_column": column_name,
        "reference_column": mapping["reference_column"],
        "bronze_column": mapping["bronze_column"],
        "bronze_type": mapping["bronze_type"],
        "bronze_nullable": mapping["bronze_nullable"],
        "mapping_source": mapping["mapping_source"],
        "notes": mapping["notes"],
        "rules": rules,
    }


def create_column_transformations(table, raw_columns, boolean_columns, sentinel_columns):
    """Create the transformed select clauses and metadata for each bronze column."""

    aliases = set()
    select_clauses = []
    column_rules = []

    for column_name, _column_type, *_ in raw_columns:
        mapping = resolve_column_mapping(table, column_name)
        alias = mapping["bronze_column"]
        if alias in aliases:
            raise ValueError(
                f"duplicate_bronze_column_name: '{column_name}' normalized to duplicate alias '{alias}'."
            )
        aliases.add(alias)

        expression, rules = build_transformation_expression(
            column_name, boolean_columns, sentinel_columns, mapping
        )
        select_clauses.append(f"    {expression} AS {quote_identifier(alias)}")
        column_rules.append(build_column_rule(column_name, mapping, rules))

    return select_clauses, column_rules


def build_bronze_select_sql(select_clauses):
    """Combine all transformed select clauses into the bronze SELECT list."""

    return ",\n".join(select_clauses)


def describe_transformed_output_schema(profile_connection, csv_path, select_sql):
    """Describe the schema produced by the bronze transformation query."""

    return profile_connection.execute(
        f"""
        DESCRIBE
        SELECT
{select_sql}
        FROM {read_csv_relation(csv_path)}
        """
    ).fetchall()


def normalize_planned_output_schema(output_schema, column_rules):
    """Build the enforced output schema using planned type and nullable metadata."""

    output_schema_map = {row[0]: row for row in output_schema}
    normalized = []
    for rule in column_rules:
        row = output_schema_map[rule["bronze_column"]]
        normalized.append(
            (
                rule["bronze_column"],
                (rule["bronze_type"] or row[1]).upper(),
                (rule["bronze_nullable"] or row[2]).upper(),
            )
        )
    return normalized


def validate_schema_mapping(column_rules, normalized_output_schema):
    """Validate if the planned output schema still matches the explicit mapping."""

    output_schema_map = {row[0]: row for row in normalized_output_schema}
    schema_mapping_errors = []

    for rule in column_rules:
        planned_column = output_schema_map[rule["bronze_column"]]
        planned_type = planned_column[1]
        planned_nullable = planned_column[2]
        expected_type = (rule["bronze_type"] or planned_type).upper()
        expected_nullable = (rule["bronze_nullable"] or planned_nullable).upper()

        if planned_type != expected_type:
            schema_mapping_errors.append(
                f"type_mismatch:{rule['bronze_column']}:expected={expected_type}:planned={planned_type}"
            )
        if planned_nullable != expected_nullable:
            schema_mapping_errors.append(
                f"nullable_mismatch:{rule['bronze_column']}:expected={expected_nullable}:planned={planned_nullable}"
            )

    if schema_mapping_errors:
        raise RuntimeError(
            "bronze_schema_mapping_mismatch: " + "; ".join(schema_mapping_errors)
        )


def plan_table(profile_connection, table, bronze_transformation_version):
    """Build the transformation plan for one raw table."""

    csv_path = resolve_raw_csv_path(table)
    raw_file_fingerprint = read_raw_file_fingerprint(csv_path)
    raw_columns = read_raw_columns(profile_connection, csv_path)
    raw_row_count = read_raw_row_count(profile_connection, csv_path)
    raw_column_count = len(raw_columns)
    raw_column_names = [row[0] for row in raw_columns]
    reference_schema_check = evaluate_schema(table, raw_column_names)
    boolean_columns = detect_boolean_columns(profile_connection, csv_path, raw_columns)
    sentinel_columns = detect_sentinel_columns(profile_connection, table, csv_path, raw_columns)
    select_clauses, column_rules = create_column_transformations(
        table, raw_columns, boolean_columns, sentinel_columns
    )
    select_sql = build_bronze_select_sql(select_clauses)
    output_schema = describe_transformed_output_schema(profile_connection, csv_path, select_sql)
    normalized_output_schema = normalize_planned_output_schema(output_schema, column_rules)
    validate_schema_mapping(column_rules, normalized_output_schema)
    validate_non_nullable_source_columns(profile_connection, csv_path, column_rules)

    return {
        "table_name": table["table_name"],
        "file_name": table["file_name"],
        "csv_path": csv_path,
        "parquet_path": BRONZE_DIR / f"{table['table_name']}.parquet",
        "raw_file_fingerprint": raw_file_fingerprint,
        "bronze_transformation_version": bronze_transformation_version,
        "select_sql": select_sql,
        "output_schema": output_schema,
        "normalized_output_schema": normalized_output_schema,
        "reference_schema_check": reference_schema_check,
        "column_rules": column_rules,
        "boolean_candidates": sorted(boolean_columns),
        "sentinel_columns": sorted(sentinel_columns),
        "raw_row_count": raw_row_count,
        "raw_column_count": raw_column_count,
        "bronze_column_count": len(normalized_output_schema),
    }
