CREATE OR REPLACE TABLE silver.credit_card_balance AS
SELECT
    sk_id_curr,
    sk_id_prev,

    months_balance,

    amt_balance,
    amt_credit_limit_actual,

    amt_drawings_current,
    amt_payment_current,
    amt_inst_min_regularity,

    cnt_drawings_current,

    -- Utilização do cartão
    CASE
        WHEN amt_credit_limit_actual > 0
        THEN amt_balance / amt_credit_limit_actual
        ELSE NULL
    END AS credit_utilization_ratio,

    -- Alta utilização
    CASE
        WHEN amt_credit_limit_actual > 0
             AND amt_balance / amt_credit_limit_actual >= 0.8
        THEN TRUE
        ELSE FALSE
    END AS high_utilization_flag,

    -- Pagamento mínimo
    CASE
        WHEN amt_payment_current <= amt_inst_min_regularity
        THEN TRUE
        ELSE FALSE
    END AS minimum_payment_flag,

    -- Possui saque/crédito rotativo
    CASE
        WHEN amt_drawings_current > 0
        THEN TRUE
        ELSE FALSE
    END AS cash_advance_flag,

    -- Muitos saques
    CASE
        WHEN cnt_drawings_current >= 5
        THEN TRUE
        ELSE FALSE
    END AS high_cash_advance_flag

FROM bronze.credit_card_balance;