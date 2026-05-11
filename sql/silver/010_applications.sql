CREATE OR REPLACE TEMP VIEW applications_stage AS
WITH base_applications AS (
    SELECT
        *,
        false AS flag_test
    FROM bronze.application_train

    UNION ALL BY NAME

    SELECT
        *,
        NULL::BOOLEAN AS target,
        true AS flag_test
    FROM bronze.application_test
)
SELECT
    *,
    ABS(days_birth) / 365.0 AS age_years,
    ABS(days_employed) / 30.0 AS employment_months,
    days_employed IS NULL AS flag_employment_missing,
    amt_credit / NULLIF(amt_income_total, 0) AS debt_income_ratio,
    amt_credit / NULLIF(amt_goods_price, 0) AS debt_good_ratio,
    days_employed IS NOT NULL AS flag_employed,
    amt_income_total / NULLIF(cnt_fam_members, 0) AS income_per_person,
    (ext_source_1 + ext_source_2 + ext_source_3) / 3.0 AS ext_source_mean,
    GREATEST(ext_source_1, ext_source_2, ext_source_3) AS ext_source_max,
    LEAST(ext_source_1, ext_source_2, ext_source_3) AS ext_source_min,
    (
        amt_req_credit_bureau_hour
        + amt_req_credit_bureau_day
        + amt_req_credit_bureau_week
        + amt_req_credit_bureau_mon
        + amt_req_credit_bureau_qrt
        + amt_req_credit_bureau_year
    ) AS total_credit_inquiries,
    (COALESCE(def_30_cnt_social_circle, 0) + COALESCE(def_60_cnt_social_circle, 0)) > 0
        AS flag_has_social_default,
    def_30_cnt_social_circle IS NULL AND def_60_cnt_social_circle IS NULL
        AS flag_social_default_na
FROM base_applications;

SET VARIABLE applications_projection = (
    WITH null_defaults AS (
        SELECT
            column_name,
            replacement_value
        FROM read_csv_auto('docs/references/silver_null_handling_mapping.csv', header = true)
        WHERE table_name = 'applications'
          AND is_active = true
          AND null_handling_rule = 'fill_constant'
    ),
    projection_rows AS (
        SELECT
            c.ordinal_position,
            CASE
                WHEN m.column_name IS NOT NULL THEN
                    'COALESCE('
                    || '"'
                    || replace(c.column_name, '"', '""')
                    || '"'
                    || ', '
                    || chr(39)
                    || replace(m.replacement_value, chr(39), chr(39) || chr(39))
                    || chr(39)
                    || ') AS '
                    || '"'
                    || replace(c.column_name, '"', '""')
                    || '"'
                ELSE
                    '"'
                    || replace(c.column_name, '"', '""')
                    || '"'
            END AS projection_sql
        FROM information_schema.columns c
        LEFT JOIN null_defaults m
          ON m.column_name = c.column_name
        WHERE c.table_name = 'applications_stage'
    ),
    projection_columns AS (
        SELECT
            string_agg(projection_sql, ', ' ORDER BY ordinal_position) AS sql_projection
        FROM projection_rows
    )
    SELECT 'SELECT ' || sql_projection || ' FROM applications_stage'
    FROM projection_columns
);

CREATE OR REPLACE TABLE silver.applications AS
SELECT *
FROM query(getvariable('applications_projection'));
