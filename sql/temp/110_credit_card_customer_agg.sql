CREATE OR REPLACE TABLE silver.credit_card_customer_agg AS
SELECT
    sk_id_curr,
    COUNT(*) AS total_credit_card_records,
    AVG(credit_utilization_ratio) AS avg_credit_utilization,
    MAX(credit_utilization_ratio) AS max_credit_utilization,
    AVG(CASE WHEN flag_high_utilization THEN 1.0 ELSE 0.0 END) AS high_utilization_ratio,
    AVG(CASE WHEN flag_minimum_payment THEN 1.0 ELSE 0.0 END) AS minimum_payment_ratio,
    AVG(CASE WHEN flag_cash_advance THEN 1.0 ELSE 0.0 END) AS cash_advance_ratio,
    SUM(CASE WHEN flag_high_cash_advance THEN 1 ELSE 0 END) AS high_cash_advance_months
FROM silver.credit_card_balance
GROUP BY sk_id_curr;
