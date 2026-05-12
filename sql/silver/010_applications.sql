CREATE OR REPLACE TABLE silver.applications AS
WITH base_applications AS (
    SELECT *, false AS flag_test
    FROM bronze.application_train

    -- garante que as colunas sejam unidas pelo nome e não pela ordem
    UNION ALL BY NAME

    SELECT *, NULL::BOOLEAN AS target, true AS flag_test
    FROM bronze.application_test
)
SELECT
    *,

   ----------------------------------------------
   -- PADRONIZAÇÃO DE DADOS PARA LEGIBILIDADE --
   ----------------------------------------------

   -- substituição de nulos categóricos - casos nulos já tratados na bronze
    CASE WHEN name_type_suite IS NULL THEN 'Unknown' ELSE name_type_suite END as name_type_suite_clean,
    CASE WHEN occupation_type IS NULL THEN 'Unknown' ELSE occupation_type END as occupation_type_clean,

   -- Contagem de dias
    ABS(days_birth) / 365.0 AS age_years,
    ABS(days_employed) / 365.0 AS employment_years,

  -----------
  -- FLAGS --
  -----------

  -- Tipo de empréstimo
  (name_contract_type = 'Cash loans') AS flag_cash_loan,
  (name_contract_type = 'Revolving loans') AS flag_revolving_loan,
  (name_contract_type = 'Consumer loans') AS flag_consumer_loan,

  -- Atividade econômica
    (days_employed IS NOT NULL) AS flag_employed,
    (days_employed IS NULL) AS flag_employment_missing,
    (name_income_type IN ('Unemployed', 'Student', 'Pensioner', 'Maternity leave')) AS flag_economically_inactive,

    (organization_type = 'Self-employed') AS flag_self_employed,
    (name_income_type = 'Unemployed') AS flag_unemployed,
    (name_income_type = 'Student') AS flag_student,
    (name_income_type = 'Pensioner') AS flag_pensioner,
    (name_income_type = 'Maternity leave') AS flag_maternity_leave,

    own_car_age IS NULL AS flag_car_age_missing,

    -- Existência de Scores Externos
    (ext_source_1 IS NULL) AS flag_ext_source_1_missing,
    (ext_source_2 IS NULL) AS flag_ext_source_2_missing,
    (ext_source_3 IS NULL) AS flag_ext_source_3_missing,

    -- Ciclo social não pagador
    CASE
        WHEN def_30_cnt_social_circle IS NULL AND def_60_cnt_social_circle IS NULL THEN NULL
        WHEN COALESCE(def_30_cnt_social_circle, 0) + COALESCE(def_60_cnt_social_circle, 0) > 0 THEN TRUE
        ELSE FALSE
    END AS flag_has_social_default,
    (def_30_cnt_social_circle IS NULL AND def_60_cnt_social_circle IS NULL) AS flag_social_default_na,

    -- Família
    (name_family_status IN ('Married','Civil marriage')) AS flag_married,


    -------------
    -- CÁCULOS --
    -------------

    --  Crédito
    CASE
        WHEN amt_credit > 0
        THEN amt_annuity / amt_credit
        ELSE NULL
    END AS annuity_credit_ratio,

    -- amt_income_total e amt_goods_price tem quase nenhum ou nenhum nulo, mas NULLIF apenas para garantir o cálculo
    (amt_credit / NULLIF(amt_income_total, 0)) AS debt_income_ratio,
    (amt_credit / NULLIF(amt_goods_price, 0)) AS debt_good_ratio,

    (amt_income_total / NULLIF(cnt_fam_members, 0)) AS income_per_person,


    -- Scores externos
    (
        CASE WHEN ext_source_1 IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN ext_source_2 IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN ext_source_3 IS NOT NULL THEN 1 ELSE 0 END
    ) AS ext_source_count,
    (COALESCE(ext_source_1, 0) + COALESCE(ext_source_2, 0) + COALESCE(ext_source_3, 0))
    / NULLIF((
            CASE WHEN ext_source_1 IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN ext_source_2 IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN ext_source_3 IS NOT NULL THEN 1 ELSE 0 END
          ),
          0
    ) AS ext_source_mean,
    CASE
        WHEN ext_source_1 IS NULL AND ext_source_2 IS NULL AND ext_source_3 IS NULL THEN NULL
        ELSE GREATEST(
            COALESCE(ext_source_1, -1),
            COALESCE(ext_source_2, -1),
            COALESCE(ext_source_3, -1)
        )
    END AS ext_source_max,
    CASE
        WHEN ext_source_1 IS NULL AND ext_source_2 IS NULL AND ext_source_3 IS NULL THEN NULL
        ELSE LEAST(
            COALESCE(ext_source_1, 999),
            COALESCE(ext_source_2, 999),
            COALESCE(ext_source_3, 999)
        )
    END AS ext_source_min,

    -- Identificação de contatos com Bureau
    CASE
        WHEN amt_req_credit_bureau_hour IS NULL
         AND amt_req_credit_bureau_day IS NULL
         AND amt_req_credit_bureau_week IS NULL
         AND amt_req_credit_bureau_mon IS NULL
         AND amt_req_credit_bureau_qrt IS NULL
         AND amt_req_credit_bureau_year IS NULL
        THEN NULL
        ELSE
            COALESCE(amt_req_credit_bureau_hour, 0)
            + COALESCE(amt_req_credit_bureau_day, 0)
            + COALESCE(amt_req_credit_bureau_week, 0)
            + COALESCE(amt_req_credit_bureau_mon, 0)
            + COALESCE(amt_req_credit_bureau_qrt, 0)
            + COALESCE(amt_req_credit_bureau_year, 0)
    END AS total_credit_inquiries,

    --------------------------
    -- INFORMAÇÃO CADASTRAL --
    --------------------------

    -- Residência
    (
        CASE WHEN apartments_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN basementarea_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN years_beginexpluatation_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN years_build_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN commonarea_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN elevators_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN entrances_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN floorsmax_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN floorsmin_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN landarea_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN livingapartments_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN livingarea_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN nonlivingapartments_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN nonlivingarea_avg IS NOT NULL THEN 1 ELSE 0 END
        + CASE WHEN totalarea_mode IS NOT NULL THEN 1 ELSE 0 END
    ) AS housing_info_filled_count,

    (
        (
            CASE WHEN apartments_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN basementarea_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN years_beginexpluatation_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN years_build_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN commonarea_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN elevators_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN entrances_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN floorsmax_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN floorsmin_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN landarea_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN livingapartments_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN livingarea_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN nonlivingapartments_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN nonlivingarea_avg IS NOT NULL THEN 1 ELSE 0 END
            + CASE WHEN totalarea_mode IS NOT NULL THEN 1 ELSE 0 END
        ) / 15.0
    ) AS housing_info_fill_rate,

    -- Contato
    (
      CASE WHEN flag_mobil THEN 1 ELSE 0 END
      + CASE WHEN flag_emp_phone THEN 1 ELSE 0 END
      + CASE WHEN flag_work_phone THEN 1 ELSE 0 END
      + CASE WHEN flag_cont_mobile THEN 1 ELSE 0 END
      + CASE WHEN flag_phone THEN 1 ELSE 0 END
      + CASE WHEN flag_email THEN 1 ELSE 0 END
    ) AS contact_info_filled_count,
    (
    (
      CASE WHEN flag_mobil THEN 1 ELSE 0 END
      + CASE WHEN flag_emp_phone THEN 1 ELSE 0 END
      + CASE WHEN flag_work_phone THEN 1 ELSE 0 END
      + CASE WHEN flag_cont_mobile THEN 1 ELSE 0 END
      + CASE WHEN flag_phone THEN 1 ELSE 0 END
      + CASE WHEN flag_email THEN 1 ELSE 0 END
    )/6.0
    ) AS contact_info_filled_rate



FROM base_applications
;