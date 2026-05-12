CREATE OR REPLACE TABLE silver.credit_card_balance AS
SELECT *,

    -----------
    -- FLAGS --
    -----------

    (amt_credit_limit_actual > 0 AND amt_balance / amt_credit_limit_actual >= 0.8) AS flag_high_utilization,
    (amt_credit_limit_actual > 0 AND amt_balance / amt_credit_limit_actual > 1) AS flag_over_utilization, -- Uso além do limite
    (amt_payment_current <= amt_inst_min_regularity) AS flag_minimum_payment,
    (amt_drawings_current > 0) AS flag_cash_advance,
    (cnt_drawings_current >= 5) AS flag_high_cash_advance,  -- Muitos saques

    --------------
    -- CÁLCULOS --
    --------------

    -- Utilização do limite do cartão
    CASE
        WHEN amt_credit_limit_actual > 0
        THEN amt_balance / amt_credit_limit_actual
        ELSE NULL
    END AS credit_utilization_ratio

FROM bronze.credit_card_balance
;