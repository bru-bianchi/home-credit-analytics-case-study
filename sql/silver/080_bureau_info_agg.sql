CREATE OR REPLACE TABLE silver.agg_bureau_external_credit_behavior AS

-- Uma linha por sk_bureau_id, agrega informação sobre crédito externo

WITH bureau_balance_agg AS (
  SELECT
      sk_bureau_id,

      -- Flags
      MAX(flag_has_dpd) AS flag_has_dpd,
      MAX(flag_severe_dpd) AS flag_severe_dpd,
      MAX(flag_recent_dpd) AS flag_has_recent_dpd,

      -- Cálculos
      COUNT(*) AS total_months,
      SUM(flag_closed_credit) AS closed_credit_months,

      SUM(CASE WHEN status_numeric = 1 THEN 1 ELSE 0 END) AS dpd_1_30_months,
      SUM(CASE WHEN status_numeric = 2 THEN 1 ELSE 0 END) AS dpd_31_60_months,
      SUM(CASE WHEN status_numeric = 3 THEN 1 ELSE 0 END) AS dpd_61_90_months,
      SUM(CASE WHEN status_numeric >= 4 THEN 1 ELSE 0 END) AS dpd_90_plus_months,

      SUM(flag_has_dpd) AS total_dpd_months,
      SUM(flag_has_dpd)/COUNT(*) AS dpd_ratio,

      SUM(flag_severe_dpd) AS severe_dpd_months,
      SUM(flag_severe_dpd)/COUNT(*) AS severe_dpd_ratio,

      MAX(status_numeric) AS max_dpd_status

  FROM silver.bureau_balance
  GROUP BY sk_bureau_id
)
SELECT bureau.*,
  (b_agg.sk_bureau_id IS NULL) AS flag_balance_missing,
  (b_agg.flag_has_dpd OR bureau.credit_day_overdue > 0) AS flag_has_dpd_agg,
  (b_agg.flag_severe_dpd OR bureau.credit_day_overdue > 60) AS flag_severe_dpd_agg,
  b_agg.flag_has_recent_dpd,

  b_agg.total_months,
  b_agg.closed_credit_months,
  b_agg.dpd_1_30_months,
  b_agg.dpd_31_60_months,
  b_agg.dpd_61_90_months,
  b_agg.dpd_90_plus_months,
  b_agg.total_dpd_months,
  b_agg.dpd_ratio,
  b_agg.severe_dpd_months,
  b_agg.severe_dpd_ratio,
  b_agg.max_dpd_status

FROM silver.bureau
LEFT JOIN bureau_balance_agg as b_agg
ON bureau.sk_bureau_id = b_agg.sk_bureau_id
;
