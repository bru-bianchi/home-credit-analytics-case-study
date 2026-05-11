CREATE OR REPLACE TABLE silver.installements_payments AS
SELECT
    sk_id_curr,
    sk_id_prev,
    num_instalment_version,
    num_instalment_number,

    days_instalment,
    days_entry_payment,

    amt_instalment,
    amt_payment,

    -- Dias de atraso
    GREATEST(
        days_entry_payment - days_instalment,
        0
    ) AS days_late,

    -- Pagamento antecipado
    CASE
        WHEN days_entry_payment < days_instalment
        THEN TRUE
        ELSE FALSE
    END AS early_payment_flag,

    -- Pagamento atrasado
    CASE
        WHEN days_entry_payment > days_instalment
        THEN TRUE
        ELSE FALSE
    END AS late_payment_flag,

    -- Pagamento parcial
    CASE
        WHEN amt_payment < amt_instalment
        THEN TRUE
        ELSE FALSE
    END AS partial_payment_flag,

    -- Ratio pagamento/parcela
    CASE
        WHEN amt_instalment > 0
        THEN amt_payment / amt_instalment
        ELSE NULL
    END AS payment_ratio,

    -- Valor faltante
    GREATEST(
        amt_instalment - amt_payment,
        0
    ) AS unpaid_amount

FROM bronze.installments_payments;