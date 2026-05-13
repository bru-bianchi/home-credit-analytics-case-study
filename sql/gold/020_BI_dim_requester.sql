CREATE OR REPLACE TABLE gold.dim_requester AS
-- Uma linha por sk_id_curr: perfil cadastral e socioeconômico do solicitante
SELECT
    ROW_NUMBER() OVER (ORDER BY a.sk_id_curr) AS requester_key,
    a.sk_id_curr,

    -- Dados demográficos e familiares
    a.code_gender,
    a.age_years,
    age_rule.band_label as age_band,
    a.name_family_status,
    a.flag_married,
    a.name_type_suite_clean,

    -- Ocupação
    a.name_income_type,
    a.occupation_type_clean,
    income_rule.band_label as income_band,
    a.flag_employed,
    a.flag_employment_missing,
    a.flag_economically_inactive,
    a.flag_self_employed,
    a.flag_unemployed,
    a.flag_student,
    a.flag_pensioner,
    a.flag_maternity_leave,
    a.employment_years,
    employment_rule.band_label as employment_tenure_band,
    a.organization_type,

    -- Educação
    a.name_education_type,

    -- Bens
    a.flag_own_car,
    a.own_car_age,
    a.flag_car_age_missing,
    a.flag_own_realty,
    a.name_housing_type,


FROM silver.applications AS a

-- Joins com a tabela de regras de faixas, localizada em 'docs/references/gold_band_rules.csv'
LEFT JOIN gold.ref_band_rules AS age_rule
ON age_rule.band_group = 'age_band'
AND (
    (a.age_years IS NULL AND age_rule.is_null_band)
    OR (
        a.age_years IS NOT NULL
        AND NOT age_rule.is_null_band
        AND (age_rule.lower_bound IS NULL OR a.age_years >= age_rule.lower_bound)
        AND (age_rule.upper_bound IS NULL OR a.age_years < age_rule.upper_bound)
    )
)

LEFT JOIN gold.ref_band_rules income_rule
ON income_rule.band_group = 'income_band'
AND (
    (a.amt_income_total IS NULL AND income_rule.is_null_band)
    OR (
        a.amt_income_total IS NOT NULL
        AND NOT income_rule.is_null_band
        AND (income_rule.lower_bound IS NULL OR a.amt_income_total >= income_rule.lower_bound)
        AND (income_rule.upper_bound IS NULL OR a.amt_income_total < income_rule.upper_bound)
    )
)

LEFT JOIN gold.ref_band_rules employment_rule
ON employment_rule.band_group = 'employment_tenure_band'
AND (
    (a.employment_years IS NULL AND employment_rule.is_null_band)
    OR (
        a.employment_years IS NOT NULL
        AND NOT employment_rule.is_null_band
        AND (employment_rule.lower_bound IS NULL OR a.employment_years >= employment_rule.lower_bound)
        AND (employment_rule.upper_bound IS NULL OR a.employment_years < employment_rule.upper_bound)
    )
)
;