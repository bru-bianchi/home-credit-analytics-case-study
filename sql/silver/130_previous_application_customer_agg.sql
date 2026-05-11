CREATE OR REPLACE TABLE silver.previous_application_customer_agg AS
SELECT
    sk_id_curr,
    COUNT(*) AS total_previous_applications,
    AVG(CASE WHEN flag_approved_application THEN 1.0 ELSE 0.0 END) AS approval_ratio,
    AVG(CASE WHEN flag_refused_application THEN 1.0 ELSE 0.0 END) AS refusal_ratio,
    AVG(CASE WHEN flag_canceled_application THEN 1.0 ELSE 0.0 END) AS cancellation_ratio,
    AVG(approved_credit_ratio) AS avg_approved_credit_ratio,
    AVG(annuity_credit_ratio) AS avg_annuity_credit_ratio,
    SUM(CASE WHEN flag_recent_application THEN 1 ELSE 0 END) AS recent_application_count,
    AVG(CASE WHEN flag_long_term_payment THEN 1.0 ELSE 0.0 END) AS long_term_payment_ratio
FROM silver.previous_application
GROUP BY sk_id_curr;
