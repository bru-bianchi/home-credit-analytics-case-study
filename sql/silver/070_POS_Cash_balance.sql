CREATE OR REPLACE TABLE silver.pos_cash_balance AS
SELECT *,

    -----------
    -- FLAGS --
    -----------

    -- DPD (Days Past Due)
    (sk_dpd > 0) AS flag_has_dpd,
    (sk_dpd > 60) AS flag_severe_dpd,

    -- Status
    (name_contract_status = 'Active') AS flag_active_contract,
    (cnt_instalment_future <= 3) AS flag_near_completion,


    --------------
    -- CÁLCULOS --
    --------------

    -- Percentual restante do contrato
    CASE
        WHEN cnt_instalment > 0
        THEN cnt_instalment_future / cnt_instalment
        ELSE NULL
    END AS remaining_installment_ratio

FROM bronze.pos_cash_balance
;
