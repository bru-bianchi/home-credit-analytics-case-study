CREATE OR REPLACE TABLE silver.posh_cash_balance AS
SELECT
    sk_id_curr,
    sk_id_prev,

    months_balance,

    cnt_instalment,
    cnt_instalment_future,

    sk_dpd,
    sk_dpd_def,

    name_contract_status,

    -- Possui atraso
    CASE
        WHEN sk_dpd > 0
        THEN TRUE
        ELSE FALSE
    END AS has_dpd_flag,

    -- Atraso severo
    CASE
        WHEN sk_dpd >= 30
        THEN TRUE
        ELSE FALSE
    END AS severe_dpd_flag,

    -- Contrato ativo
    CASE
        WHEN name_contract_status = 'Active'
        THEN TRUE
        ELSE FALSE
    END AS active_contract_flag,

    -- Poucas parcelas restantes
    CASE
        WHEN cnt_instalment_future <= 3
        THEN TRUE
        ELSE FALSE
    END AS near_completion_flag,

    -- Percentual restante do contrato
    CASE
        WHEN cnt_instalment > 0
        THEN cnt_instalment_future / cnt_instalment
        ELSE NULL
    END AS remaining_installment_ratio

FROM bronze.pos_cash_balance;