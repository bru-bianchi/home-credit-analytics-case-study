CREATE OR REPLACE TABLE silver.bureau_balance_agg AS
WITH bureau_balance_enriched AS (
    SELECT
        sk_bureau_id,
        status_numeric,
        flag_has_dpd,
        flag_severe_dpd,
        flag_recent_dpd,
        flag_closed_credit,
        months_balance_abs,

        -- Penaliza mais fortemente DPDs recentes sem exigir coluna adicional na base.
        COALESCE(status_numeric, 0) / NULLIF(months_balance_abs + 1, 0) AS dpd_weighted_score
    FROM silver.bureau_balance
)
SELECT
    sk_bureau_id,
    COUNT(*) AS total_months,
    AVG(status_numeric) AS avg_dpd,
    MAX(status_numeric) AS max_dpd,
    SUM(CASE WHEN flag_has_dpd THEN 1 ELSE 0 END) AS total_dpd_months,
    AVG(CASE WHEN flag_has_dpd THEN 1.0 ELSE 0.0 END) AS dpd_ratio,
    SUM(CASE WHEN flag_severe_dpd THEN 1 ELSE 0 END) AS severe_dpd_months,
    MAX(CASE WHEN flag_recent_dpd THEN 1 ELSE 0 END) > 0 AS has_recent_dpd,
    AVG(dpd_weighted_score) AS avg_dpd_weighted_score,
    SUM(CASE WHEN flag_closed_credit THEN 1 ELSE 0 END) AS closed_credit_months
FROM bureau_balance_enriched
GROUP BY sk_bureau_id;
