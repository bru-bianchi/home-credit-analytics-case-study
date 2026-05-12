CREATE OR REPLACE TABLE silver.bureau_balance AS
SELECT *,

    CASE
        WHEN status = 'X' THEN NULL
        WHEN status = 'C' THEN 0
        ELSE CAST(status AS INTEGER)
    END AS status_numeric,

    -----------
    -- FLAGS --
    -----------

    -- DPD (Days Past Due)
    (status IN ('1', '2', '3', '4', '5')) AS flag_has_dpd, -- qualquer período
    (status IN ('3', '4', '5')) AS flag_severe_dpd, -- 60+ dias
    (ABS(months_balance) <= 1 AND status IN ('1', '2', '3', '4', '5')) AS flag_recent_dpd,

    (status = 'C') AS flag_closed_credit,
    (status = 'X') aS flag_missing_status,

   --------------
   -- CÁLCULOS --
   --------------
   ABS(months_balance) AS months_balance_abs

FROM bronze.bureau_balance
;
