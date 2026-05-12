CREATE OR REPLACE TABLE silver.installments_payments AS
SELECT *,

    -----------
    -- FLAGS --
    -----------

    (days_entry_payment < days_instalment) AS flag_early_payment,
    (days_entry_payment > days_instalment) AS flag_late_payment,
    (amt_payment < amt_instalment) AS flag_partial_payment,
    (num_instalment_number = 0) as flag_credit_card,


    --------------
    -- CÁLCULOS --
    --------------

    GREATEST(days_entry_payment - days_instalment,0) AS days_late,

    CASE
        WHEN amt_instalment > 0
        THEN amt_payment / amt_instalment
        ELSE NULL
    END AS payment_ratio,

    GREATEST(
        amt_instalment - amt_payment,
        0
    ) AS unpaid_amount

FROM bronze.installments_payments
;
