-- CREATE OR REPLACE TABLE silver.previous_application AS
SELECT
    *,

   ----------------------------------------------
   -- PADRONIZAÇÃO DE DADOS PARA LEGIBILIDADE --
   ----------------------------------------------

   -- substituição de nulos categóricos - casos nulos já tratados na bronze
    CASE WHEN name_type_suite IS NULL THEN 'Unknown' ELSE name_type_suite END as name_type_suite_clean,


    -----------
    -- FLAGS --
    -----------

    -- Razão do empréstimo
    (name_goods_category IS NULL) as flag_goods_category_known,

    -- Situação empréstimo
    (ABS(days_decision) <= 30) AS flag_recent_application,
    (cnt_payment >= 24) AS flag_long_term_payment,

    (name_contract_status = 'Approved') AS flag_approved_application,
    (name_contract_status = 'Refused') AS flag_refused_application,
    (name_contract_status = 'Canceled') AS flag_canceled_application,

    -- Tipo de empréstimo
    (name_contract_type = 'Cash loans') AS flag_cash_loan,
    (name_contract_type = 'Revolving loans') flag_revolving_loan,
    (name_contract_type = 'Consumer loans') AS flag_consumer_loan,

    -- Tipo de cliente
    (name_client_type = 'Repeater') AS flag_repeater,

    -------------
    -- CÁCULOS --
    -------------

    amt_credit - amt_application AS credit_application_diff,

    CASE
        WHEN amt_goods_price > 0
        THEN amt_application / amt_goods_price
        ELSE NULL
    END AS goods_vs_application_ratio,

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

FROM bronze.previous_application
;
