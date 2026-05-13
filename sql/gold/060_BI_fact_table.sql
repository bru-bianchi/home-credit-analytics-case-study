-- Uma linha por sk_id_curr: fato central para o dashboard de risco

CREATE OR REPLACE TABLE gold.fact_credit_risk AS
WITH
-- Parte 1: variáveis da aplicação atual (sk_id_curr)
applications_info AS (
    SELECT
            -- Identificação do empréstimo atual
            a.sk_id_curr,

            -- Inadimplência
            a.target,

            -- Valores financeiros do contrato
            a.amt_credit, -- valor do crédito
            a.amt_annuity, -- valor da anuidade
            a.amt_goods_price, -- valor dos bens para qual o empréstimo foi requisitado
            a.amt_income_total,

            -- Métricas do contrato
            a.annuity_credit_ratio,
            a.loan_income_ratio,
            a.annuity_income_ratio,
            a.debt_good_ratio,

            -- Métricas do cliente
            a.income_per_person,
            a.cnt_children,
            a.cnt_fam_members,
            a.employment_years,

            -- Histórico Externo
            a.ext_source_count,
            a.ext_source_mean,
            a.ext_source_max,
            a.ext_source_min,
            a.total_credit_inquiries,

            -- Métricas de completude cadastral
            a.housing_info_filled_count,
            a.housing_info_fill_rate,
            a.contact_info_filled_count,
            a.contact_info_filled_rate,
            a.ext_source_missing_count,
            a.ext_source_fill_rate,
            a.social_circle_info_filled_count,
            a.social_circle_info_filled_rate,
            a.document_provided_count,
            a.document_provided_rate,


        FROM silver.applications a
        WHERE a.flag_test = false -- não faz sentido trazermos dados de teste porque queremos analisar os padrões de quem já sabemos

),

-- Parte 2: Métricas de histórico externo
external_credit_info AS (

    SELECT
        -- Identificação do empréstimo atual
        sk_id_curr,

        COUNT(*) AS bureau_total_loans,
        SUM(flag_active_credit) AS bureau_active_loans,
        SUM(flag_bad_debt) AS bureau_bad_debt_loans,

        SUM(amt_credit_sum) AS bureau_total_credit,
        AVG(amt_credit_sum) AS bureau_avg_credit,

        SUM(CASE WHEN flag_has_dpd_agg THEN 1 ELSE 0 END) as bureau_total_loans_with_dpd,
        SUM(CASE WHEN flag_severe_dpd_agg THEN 1 ELSE 0 END) as bureau_total_loans_with_severe_dpd,

        -- Se 'flag_balance_missing' foi true, não teremos informação sobre recência ou status mensal de DPD
        SUM(CASE WHEN NOT flag_balance_missing THEN flag_recent_credit ELSE NULL END) AS bureau_recent_credit_count,
        MAX(CASE WHEN NOT flag_balance_missing THEN max_dpd_status ELSE NULL END) AS bureau_max_dpd_status,

        -- Se DPD, qual o valor atual (pode ser 0 caso já tenha sido quitado)
        SUM(amt_credit_sum_overdue) AS bureau_total_overdue_amount,
        AVG(overdue_credit_ratio) AS bureau_avg_overdue_credit_ratio,

        -- Qual valor em aberto das dívidas (média e máximo)
        AVG(debt_credit_ratio) AS bureau_avg_debt_credit_ratio,
        MAX(debt_credit_ratio) AS bureau_max_debt_credit_ratio,

        AVG(credit_age_days) AS bureau_avg_credit_age_days

    FROM silver.agg_bureau_external_credit_behavior
    GROUP BY sk_id_curr
),
-- Parte 3: Métricas de histórico interno
internal_credit_info AS (
    SELECT
      sk_id_curr,

      -- Valores e ratios
      SUM(amt_application) AS prev_total_application_amt,
      SUM(amt_credit) AS prev_total_given_credit,
      AVG(amt_credit) AS prev_avg_given_credit,

      CASE
          WHEN SUM(amt_application) > 0
          THEN SUM(amt_credit) / SUM(amt_application)
          ELSE NULL
        END AS prev_approved_credit_ratio,

        CASE
            WHEN SUM(amt_goods_price) > 0
            THEN SUM(amt_application) / SUM(amt_goods_price)
            ELSE NULL
        END AS prev_goods_vs_application_ratio,

      -- Contagem
      COUNT(*) AS prev_applications_total,

      -- Status dos empréstimos
      SUM(flag_approved_application) AS prev_applications_approved,
      SUM(flag_refused_application) AS prev_applications_refused,
      SUM(flag_canceled_application) AS prev_applications_canceled,

      -- Tipos
      SUM(flag_cash_loan) AS prev_cash_loan_count,
      SUM(flag_revolving_loan) AS prev_revolving_loan_count,
      SUM(flag_consumer_loan) AS prev_consumer_loan_count,

      -- Uso de cartão
      MAX(max_credit_utilization) AS max_credit_utilization,
      SUM(total_amt_balance)/SUM(total_credit_limit) AS avg_credit_utilization,

      -- Pagamentos de parcelas
      SUM(installment_total_unpaid_amount) AS prev_unpaid_amount_for_installments, -- pode ter sido quitado, mas em algum momento aconteceu
      MAX(max_payment_ratio) AS max_payment_ratio,
      SUM(total_amt_payment)/SUM(total_amt_installment) AS avg_payment_ratio,

      -- POS
      SUM(pos_total_dpd) AS pos_total_dpd,
      AVG(pos_total_dpd) AS pos_avg_dpd,

      -- Temporais
      SUM(flag_recent_application) AS prev_recent_application_count,
      SUM(flag_long_term_payment) AS prev_long_term_pay_application_count

    FROM silver.agg_internal_historical_behavior
    GROUP BY sk_id_curr
)

SELECT
    -- Chave da aplicação
    applications_info.sk_id_curr,

    -- Chaves das tabelas dimensão
    requester.requester_key,
    contract.contract_key,
    risk_segment.risk_segment_key, -- engloba risco interno e externo

    -- Métricas da aplicação
    applications_info.target,
    applications_info.amt_credit,
    applications_info.amt_annuity,
    applications_info.amt_goods_price,
    applications_info.amt_income_total,
    applications_info.annuity_credit_ratio,
    applications_info.annuity_income_ratio,
    applications_info.loan_income_ratio,
    applications_info.debt_good_ratio,
    applications_info.income_per_person,
    applications_info.cnt_children,
    applications_info.cnt_fam_members,
    applications_info.employment_years,
    applications_info.ext_source_count,
    applications_info.ext_source_mean,
    applications_info.ext_source_max,
    applications_info.ext_source_min,
    applications_info.total_credit_inquiries,
    applications_info.housing_info_filled_count,
    applications_info.housing_info_fill_rate,
    applications_info.contact_info_filled_count,
    applications_info.contact_info_filled_rate,
    applications_info.ext_source_missing_count,
    applications_info.ext_source_fill_rate,
    applications_info.social_circle_info_filled_count,
    applications_info.social_circle_info_filled_rate,
    applications_info.document_provided_count,
    applications_info.document_provided_rate,

    -- Métricas de histórico externo
    external_credit_info.bureau_total_loans,
    external_credit_info.bureau_active_loans,
    external_credit_info.bureau_bad_debt_loans,
    external_credit_info.bureau_total_credit,
    external_credit_info.bureau_avg_credit,
    external_credit_info.bureau_total_loans_with_dpd,
    external_credit_info.bureau_total_loans_with_severe_dpd,
    external_credit_info.bureau_recent_credit_count,
    external_credit_info.bureau_max_dpd_status,
    external_credit_info.bureau_total_overdue_amount,
    external_credit_info.bureau_avg_overdue_credit_ratio,
    external_credit_info.bureau_avg_debt_credit_ratio,
    external_credit_info.bureau_max_debt_credit_ratio,
    external_credit_info.bureau_avg_credit_age_days,

    -- Métricas de histórico interno
    internal_credit_info.prev_total_application_amt,
    internal_credit_info.prev_total_given_credit,
    internal_credit_info.prev_avg_given_credit,
    internal_credit_info.prev_approved_credit_ratio,
    internal_credit_info.prev_goods_vs_application_ratio,
    internal_credit_info.prev_applications_total,
    internal_credit_info.prev_applications_approved,
    internal_credit_info.prev_applications_refused,
    internal_credit_info.prev_applications_canceled,
    internal_credit_info.prev_cash_loan_count,
    internal_credit_info.prev_revolving_loan_count,
    internal_credit_info.prev_consumer_loan_count,
    internal_credit_info.max_credit_utilization,
    internal_credit_info.avg_credit_utilization,
    internal_credit_info.prev_unpaid_amount_for_installments,
    internal_credit_info.max_payment_ratio,
    internal_credit_info.avg_payment_ratio,
    internal_credit_info.pos_total_dpd,
    internal_credit_info.pos_avg_dpd,
    internal_credit_info.prev_recent_application_count,
    internal_credit_info.prev_long_term_pay_application_count

FROM applications_info -- base principal, core da análise

LEFT JOIN external_credit_info
ON applications_info.sk_id_curr = external_credit_info.sk_id_curr

LEFT JOIN internal_credit_info
ON applications_info.sk_id_curr = internal_credit_info.sk_id_curr

LEFT JOIN gold.dim_requester AS requester
    ON applications_info.sk_id_curr = requester.sk_id_curr

LEFT JOIN gold.dim_contract AS contract
    ON applications_info.sk_id_curr = contract.sk_id_curr

LEFT JOIN gold.dim_risk_segment AS risk_segment
    ON applications_info.sk_id_curr = risk_segment.sk_id_curr
;