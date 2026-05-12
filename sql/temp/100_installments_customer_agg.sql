CREATE OR REPLACE TABLE silver.installments_customer_agg AS
SELECT
    sk_id_curr,
    COUNT(*) AS total_installments,
    AVG(days_late) AS avg_days_late,
    MAX(days_late) AS max_days_late,
    AVG(CASE WHEN flag_late_payment THEN 1.0 ELSE 0.0 END) AS late_payment_ratio,
    AVG(CASE WHEN flag_partial_payment THEN 1.0 ELSE 0.0 END) AS partial_payment_ratio,
    AVG(payment_ratio) AS avg_payment_ratio,
    SUM(unpaid_amount) AS total_unpaid_amount,
    SUM(CASE WHEN flag_late_payment THEN 1 ELSE 0 END) AS total_late_payments
FROM silver.installements_payments
GROUP BY sk_id_curr;
