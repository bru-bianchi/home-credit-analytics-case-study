--CREATE OR REPLACE TABLE silver.bureau_info_agg AS
-- Uma linha por sk_bureau_id

WITH bureau_balance_agg AS (
  SELECT
      sk_bureau_id,

      -- Flags
      MAX(flag_has_dpd) AS flag_has_dpd,
      MAX(flag_recent_dpd) AS flag_has_recent_dpd,

      -- Cálculos
      COUNT(*) AS total_months,
      SUM(flag_closed_credit) AS closed_credit_months,
      SUM(flag_has_dpd) AS total_dpd_months,
      SUM(flag_has_dpd)/COUNT(*) AS dpd_ratio,

      SUM(flag_severe_dpd) AS severe_dpd_months,
      SUM(flag_severe_dpd)/COUNT(*) AS severe_dpd_ratio,

      MAX(status_numeric) AS max_dpd_status

  FROM silver.bureau_balance
  GROUP BY sk_bureau_id
)
SELECT bureau.*,
  case when b_agg.sk_bureau_id is null then true else false end as flag_balance_missing,
  b_agg.flag_has_dpd,
  b_agg.flag_has_recent_dpd,

  b_agg.total_months,
  b_agg.closed_credit_months,
  b_agg.total_dpd_months,
  b_agg.dpd_ratio,
  b_agg.severe_dpd_months,
  b_agg.severe_dpd_ratio,
  b_agg.max_dpd_status

FROM silver.bureau
LEFT JOIN bureau_balance_agg as b_agg
ON bureau.sk_bureau_id = b_agg.sk_bureau_id
;