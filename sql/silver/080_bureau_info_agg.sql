CREATE OR REPLACE TABLE silver.bureau_info_agg AS
-- one row per sk_bureau_id
WITH bureau_balance_agg AS (
  SELECT
      sk_bureau_id,
      COUNT(*) AS total_months,
      SUM(CASE WHEN flag_closed_credit THEN 1 ELSE 0 END) AS closed_credit_months,
      MAX(status_numeric) AS max_dpd,
      MAX(CASE WHEN flag_has_dpd THEN 1 ELSE 0 END) > 0 AS flag_has_dpd,
      SUM(CASE WHEN flag_has_dpd THEN 1 ELSE 0 END) AS total_dpd_months,
      AVG(CASE WHEN flag_has_dpd THEN 1.0 ELSE 0.0 END) AS dpd_ratio,
      SUM(CASE WHEN flag_severe_dpd THEN 1 ELSE 0 END) AS severe_dpd_months,
      MAX(CASE WHEN flag_recent_dpd THEN 1 ELSE 0 END) > 0 AS flag_has_recent_dpd,

  FROM silver.bureau_balance
  GROUP BY sk_bureau_id
)
SELECT bureau.*,
  case when b_agg.total_months is null then true else false end as flag_balance_missing,
  b_agg.total_months,
  b_agg.max_dpd,
  b_agg.flag_has_dpd,
  b_agg.dpd_ratio,
  b_agg.total_dpd_months,
  b_agg.severe_dpd_months,
  b_agg.flag_has_recent_dpd,
  b_agg.closed_credit_months

FROM silver.bureau
LEFT JOIN bureau_balance_agg as b_agg
ON bureau.sk_bureau_id = b_agg.sk_bureau_id
;