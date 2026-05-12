CREATE OR REPLACE TABLE silver.pos_cash_customer_agg AS
SELECT
    sk_id_curr,
    COUNT(*) AS total_pos_cash_records,
    AVG(CASE WHEN flag_has_dpd THEN 1.0 ELSE 0.0 END) AS dpd_ratio,
    AVG(CASE WHEN flag_severe_dpd THEN 1.0 ELSE 0.0 END) AS severe_dpd_ratio,
    AVG(remaining_installment_ratio) AS avg_remaining_installment_ratio,
    SUM(CASE WHEN flag_active_contract THEN 1 ELSE 0 END) AS active_contracts,
    SUM(CASE WHEN flag_near_completion THEN 1 ELSE 0 END) AS near_completion_contracts
FROM silver.pos_cash_balance
GROUP BY sk_id_curr;
