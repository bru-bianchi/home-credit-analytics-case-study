CREATE OR REPLACE TABLE silver.bureau_customer_agg AS
SELECT
    sk_id_curr,
    COUNT(*) AS total_bureau_loans,
    SUM(CASE WHEN flag_active_credit THEN 1 ELSE 0 END) AS active_loans,
    SUM(CASE WHEN flag_bad_debt THEN 1 ELSE 0 END) AS bad_debt_loans,
    SUM(CASE WHEN flag_has_overdue THEN 1 ELSE 0 END) AS overdue_loans,
    AVG(debt_credit_ratio) AS avg_debt_credit_ratio,
    MAX(debt_credit_ratio) AS max_debt_credit_ratio,
    AVG(overdue_credit_ratio) AS avg_overdue_credit_ratio,
    SUM(amt_credit_sum_overdue) AS total_overdue_amount,
    AVG(credit_age_days) AS avg_credit_age_days,
    SUM(CASE WHEN flag_recent_credit THEN 1 ELSE 0 END) AS recent_credit_count
FROM silver.bureau
GROUP BY sk_id_curr;
