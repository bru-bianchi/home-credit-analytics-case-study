CREATE OR REPLACE TABLE silver.bureau_balance AS
SELECT
    sk_bureau_id,
    months_balance,
    status,

    CASE
        WHEN status = 'X' THEN NULL
        WHEN status = 'C' THEN 0
        ELSE CAST(status AS INTEGER)
    END AS status_numeric,

    CASE
        WHEN status IN ('1', '2', '3', '4', '5') THEN TRUE
        ELSE FALSE
    END AS flag_has_dpd,

    CASE
        WHEN status IN ('3', '4', '5') THEN TRUE
        ELSE FALSE
    END AS flag_severe_dpd,

    CASE
        WHEN status = 'C' THEN TRUE
        ELSE FALSE
    END AS flag_closed_credit,

    CASE
        WHEN status = 'X' THEN TRUE
        ELSE FALSE
    END AS flag_missing_status,

    ABS(months_balance) AS months_balance_abs,

    CASE
        WHEN ABS(months_balance) <= 3
             AND status IN ('1', '2', '3', '4', '5')
        THEN TRUE
        ELSE FALSE
    END AS flag_recent_dpd,

    CASE
        WHEN status IN ('X', 'C', '0') THEN 'no_dpd'
        WHEN status IN ('1', '2') THEN 'low_dpd'
        WHEN status = '3' THEN 'medium_dpd'
        WHEN status IN ('4', '5') THEN 'severe_dpd'
        ELSE 'unknown'
    END AS dpd_status
FROM bronze.bureau_balance;
