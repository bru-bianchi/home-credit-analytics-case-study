CREATE SCHEMA IF NOT EXISTS silver;

CREATE OR REPLACE TABLE silver.previous_application AS
SELECT
    *,

    amt_credit - amt_application AS credit_application_diff,

    CASE
        WHEN amt_application > 0
        THEN amt_credit / amt_application
        ELSE NULL
    END AS approved_credit_ratio,

    CASE
        WHEN amt_credit > 0
        THEN amt_annuity / amt_credit
        ELSE NULL
    END AS annuity_credit_ratio,

    CASE
        WHEN ABS(days_decision) <= 30 THEN TRUE
        ELSE FALSE
    END AS flag_recent_application,

    CASE
        WHEN name_contract_status = 'Approved' THEN TRUE
        ELSE FALSE
    END AS flag_approved_application,

    CASE
        WHEN name_contract_status = 'Refused' THEN TRUE
        ELSE FALSE
    END AS flag_refused_application,

    CASE
        WHEN name_contract_status = 'Canceled' THEN TRUE
        ELSE FALSE
    END AS flag_canceled_application,

    CASE
        WHEN name_contract_type = 'Revolving loans' THEN TRUE
        ELSE FALSE
    END AS revolving_loan_flag,

    CASE
        WHEN name_contract_type = 'Consumer loans' THEN TRUE
        ELSE FALSE
    END AS flag_consumer_loan,

    CASE
        WHEN cnt_payment >= 24 THEN TRUE
        ELSE FALSE
    END AS flag_long_term_payment

FROM bronze.previous_application;
