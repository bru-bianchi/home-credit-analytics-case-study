CREATE OR REPLACE TABLE silver.bureau AS
SELECT
    *,

  -----------
  -- FLAGS --
  -----------

  -- Missing
  (amt_credit_sum_debt IS NULL) AS flag_debt_missing,
    (amt_annuity IS NULL) AS flag_missing_annuity,

  -- Situaçõ
  (COALESCE(amt_credit_sum_overdue, 0) > 0) AS flag_has_overdue,
  (ABS(days_credit) <= 30) AS flag_recent_credit,
  (cnt_credit_prolong > 0) AS flag_credit_was_prolonged,

  (credit_active = 'Active') AS flag_active_credit,
  (credit_active = 'Bad debt') AS flag_bad_debt,

  -- Tipos
  (credit_type = 'Consumer credit') AS flag_consumer_credit,
  (credit_type = 'Credit card') AS flag_credit_card,
  (credit_type = 'Car loan') AS flag_car_loan,
  (credit_type = 'Mortgage') AS flag_mortgage,


  --------------
  -- CÁLCULOS --
  --------------

    -- Ratios
    CASE
        WHEN amt_credit_sum > 0 and amt_credit_sum_debt IS NOT NULL
        THEN amt_credit_sum_debt / amt_credit_sum
        ELSE NULL
    END AS debt_credit_ratio,

    CASE
        WHEN amt_credit_sum > 0 and amt_credit_sum_overdue IS NOT NULL
        THEN amt_credit_sum_overdue / amt_credit_sum
        ELSE NULL
    END AS overdue_credit_ratio,

    -- Informações do crédito legíveis
    ABS(days_credit) AS credit_age_days,

FROM bronze.bureau
;
