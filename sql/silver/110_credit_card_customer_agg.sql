CREATE OR REPLACE TABLE silver.credit_card_customer_agg AS
SELECT
    sk_id_curr,
    COUNT(*) AS total_credit_card_records,
    AVG(credit_utilization_ratio) AS avg_credit_utilization,
    MAX(credit_utilization_ratio) AS max_credit_utilization,
    AVG(CASE WHEN high_utilization_flag THEN 1.0 ELSE 0.0 END) AS high_utilization_ratio,
    AVG(CASE WHEN minimum_payment_flag THEN 1.0 ELSE 0.0 END) AS minimum_payment_ratio,
    AVG(CASE WHEN cash_advance_flag THEN 1.0 ELSE 0.0 END) AS cash_advance_ratio,
    SUM(CASE WHEN high_cash_advance_flag THEN 1 ELSE 0 END) AS high_cash_advance_months
FROM silver.credit_card_balance
GROUP BY sk_id_curr;
