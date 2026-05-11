CREATE OR REPLACE TABLE silver.bureau AS
SELECT
    *,

    COALESCE(amt_credit_sum_debt, 0) AS amt_credit_sum_debt_clean,

    CASE
        WHEN amt_credit_sum_debt IS NULL THEN TRUE
        ELSE FALSE
    END AS flag_debt_missing,

    CASE
        WHEN amt_credit_sum > 0
        THEN COALESCE(amt_credit_sum_debt, 0) / amt_credit_sum
        ELSE NULL
    END AS debt_credit_ratio,

    CASE
        WHEN amt_credit_sum > 0
        THEN COALESCE(amt_credit_sum_overdue, 0) / amt_credit_sum
        ELSE NULL
    END AS overdue_credit_ratio,

    CASE
        WHEN COALESCE(amt_credit_sum_overdue, 0) > 0 THEN TRUE
        ELSE FALSE
    END AS flag_has_overdue,

    CASE
        WHEN credit_active = 'Active' THEN TRUE
        ELSE FALSE
    END AS is_active_credit,

    CASE
        WHEN credit_active = 'Bad debt' THEN TRUE
        ELSE FALSE
    END AS is_bad_debt,

    ABS(days_credit) AS credit_age_days,

    CASE
        WHEN ABS(days_credit) <= 30 THEN TRUE
        ELSE FALSE
    END AS recent_credit_flag
FROM bronze.bureau;
