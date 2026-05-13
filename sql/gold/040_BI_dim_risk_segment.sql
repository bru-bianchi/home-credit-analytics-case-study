CREATE OR REPLACE TABLE gold.dim_risk_segment AS

-- Uma linha por sk_id_curr: segmentacoes e indicadores para quebra de risco.
-- Derivada da feature store para manter uma unica fonte de regras e features.

WITH internal_credit AS (
   SELECT sk_id_curr,
       MAX(flag_repeater) as flag_repeater,

       -- Uso de cartão
        MAX(flag_card_high_utilization) AS flag_high_card_user,
        MAX(flag_card_over_utilization) AS flag_has_overused_card,

        -- Pagamento de parcelas
        MAX(flag_installment_late_payment) AS flag_has_had_late_payment,

        -- Comportamento POS
        MAX(flag_pos_dpd) AS internal_pos_dpd,
        MAX(flag_pos_severe_dpd) AS internal_pos_severe_dpd,


   FROM silver.agg_internal_historical_behavior
    GROUP BY sk_id_curr

),
external_credit AS (
    SELECT sk_id_curr,

    MAX(flag_has_dpd_agg) AS external_had_dpd,
    MAX(flag_severe_dpd_agg) AS external_severe_dpd,
    MAX(flag_bad_debt) AS external_bad_debt,
    MAX(flag_recent_credit) AS external_recent_credit,
    MAX(max_dpd_status) AS max_external_dpd_status

    FROM silver.agg_bureau_external_credit_behavior
    GROUP BY sk_id_curr
)

SELECT
    ROW_NUMBER() OVER (ORDER BY a.sk_id_curr) AS risk_segment_key,
    a.sk_id_curr,

    internal.flag_repeater,
    internal.flag_high_card_user,
    internal.flag_has_overused_card,
    internal.flag_has_had_late_payment,
    internal.internal_pos_dpd,
    internal.internal_pos_severe_dpd,

    bureau.external_had_dpd,
    bureau.external_severe_dpd,
    bureau.external_bad_debt,
    bureau.external_recent_credit,
    bureau.max_external_dpd_status,

    -- Faixas de Métricas
    dti_rule.band_label as dti_band,
    score_rule.band_label as mean_score_band,
    annuity_income_rule.band_label as annuity_income_band,

    -- Completudo de info de risco
    CASE WHEN internal.sk_id_curr IS NULL THEN true ELSE false END AS flag_missing_prev_applications_info,
    CASE WHEN bureau.sk_id_curr IS NULL THEN true ELSE false END AS flag_missing_bureau_info,

    -- Score externo
    a.ext_source_1,
    a.ext_source_2,
    a.ext_source_3,
    a.flag_ext_source_1_missing,
    a.flag_ext_source_2_missing,
    a.flag_ext_source_3_missing

FROM silver.applications AS a

LEFT JOIN  external_credit as bureau
ON a.sk_id_curr = bureau.sk_id_curr

LEFT JOIN internal_credit as internal
ON a.sk_id_curr = internal.sk_id_curr

LEFT JOIN gold.ref_band_rules dti_rule
ON dti_rule.band_group = 'dti_band'
AND (
    (a.debt_income_ratio IS NULL AND dti_rule.is_null_band)
    OR (
        a.debt_income_ratio IS NOT NULL
        AND NOT dti_rule.is_null_band
        AND (dti_rule.lower_bound IS NULL OR a.debt_income_ratio >= dti_rule.lower_bound)
        AND (dti_rule.upper_bound IS NULL OR a.debt_income_ratio < dti_rule.upper_bound)
    )
)

LEFT JOIN gold.ref_band_rules score_rule
        ON score_rule.band_group = 'score_band'
       AND (
            (a.ext_source_mean IS NULL AND score_rule.is_null_band)
            OR (
                a.ext_source_mean IS NOT NULL
                AND NOT score_rule.is_null_band
                AND (score_rule.lower_bound IS NULL OR a.ext_source_mean >= score_rule.lower_bound)
                AND (score_rule.upper_bound IS NULL OR a.ext_source_mean < score_rule.upper_bound)
            )
       )

LEFT JOIN gold.ref_band_rules annuity_income_rule
        ON annuity_income_rule.band_group = 'annuity_income_band'
       AND (
            (a.annuity_income_ratio IS NULL AND annuity_income_rule.is_null_band)
            OR (
                a.annuity_income_ratio IS NOT NULL
                AND NOT annuity_income_rule.is_null_band
                AND (annuity_income_rule.lower_bound IS NULL OR a.annuity_income_ratio >= annuity_income_rule.lower_bound)
                AND (annuity_income_rule.upper_bound IS NULL OR a.annuity_income_ratio < annuity_income_rule.upper_bound)
            )
       )
;
