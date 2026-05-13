CREATE OR REPLACE TABLE gold.credit_risk_feature_store AS

-- Uma linha por sk_id_curr - agrega informações de comportamento, severidade, histórico, agregando informações
--     de todas as tabelas disponíveis na silver

WITH bureau_info AS (
  SELECT
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

previous_application_info AS (

  SELECT
      sk_id_curr,
      
      COUNT(*) AS prev_applications_total,
      
      -- Status dos empréstimos
      SUM(flag_approved_application) AS prev_applications_approved,
      SUM(flag_refused_application) AS prev_applications_refused,
      SUM(flag_canceled_application) AS prev_applications_canceled,
  
      -- Tipos
      SUM(flag_cash_loan) AS prev_cash_loan_count,
      SUM(flag_revolving_loan) AS prev_revolving_loan_count,
      SUM(flag_consumer_loan) AS prev_consumer_loan_count,
  
      -- Características de Previous Applications
      MAX(flag_repeater) AS flag_repeater,
  
      -- As features abaixo dizem respeito às bases históricas, e as flags mostram se em alguma das aplicações
      -- anteriores aquela situação aconteceu
      
      -- Características de uso de cartão -- não disponíveis se 'flag_credit_card_info_missing' = true
      MAX(flag_card_high_utilization) AS flag_high_card_user,
      MAX(flag_card_over_utilization) AS flag_has_overused_card,
      MAX(max_credit_utilization) AS max_credit_utilization,
      SUM(total_amt_balance)/SUM(total_credit_limit) AS avg_credit_utilization,
  
      -- Características de pagamentos de parcelas -- não disponíveis se 'flag_installments_info_missing' = true
      MAX(flag_installment_late_payment) AS flag_has_had_late_payment,
      SUM(installment_total_unpaid_amount) AS prev_unpaid_amount_for_installments, -- pode ter sido quitado, mas em algum momento aconteceu
      MAX(max_payment_ratio) AS max_payment_ratio,
      SUM(total_amt_payment)/SUM(total_amt_installment) AS avg_payment_ratio,
  
      -- Características de POS - não disponíveis se 'flag_pos_info_missing' = true
      MAX(flag_pos_dpd) AS flag_has_had_pos_dpd,
      MAX(flag_pos_severe_dpd) AS flag_has_had_pos_severe_dpd,
      SUM(pos_total_dpd) AS pos_total_dpd,
      AVG(pos_total_dpd) AS pos_avg_dpd,
  
      -- Temporais
      SUM(flag_recent_application) AS prev_recent_application_count,
      SUM(flag_long_term_payment) AS prev_long_term_pay_application,
  
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
      END AS prev_goods_vs_application_ratio
          
  FROM silver.agg_internal_historical_behavior
  GROUP BY sk_id_curr
)

SELECT applications.sk_id_curr,

      CASE WHEN previous_application_info.sk_id_curr IS NULL THEN true ELSE false END AS flag_missing_prev_applications_info,
      CASE WHEN bureau_info.sk_id_curr IS NULL THEN true ELSE false END AS flag_missing_bureau_info,
       
       bureau_info.bureau_total_loans,
       bureau_info.bureau_active_loans,
       bureau_info.bureau_bad_debt_loans,
       bureau_info.bureau_total_credit,
       bureau_info.bureau_avg_credit,
       bureau_info.bureau_total_loans_with_dpd,
       bureau_info.bureau_total_loans_with_severe_dpd,
       bureau_info.bureau_recent_credit_count,
       bureau_info.bureau_max_dpd_status,
       bureau_info.bureau_total_overdue_amount,
       bureau_info.bureau_avg_overdue_credit_ratio,
       bureau_info.bureau_avg_debt_credit_ratio,
       bureau_info.bureau_max_debt_credit_ratio,
       bureau_info.bureau_avg_credit_age_days,

      previous_application_info.prev_applications_total,
      previous_application_info.prev_applications_approved,
      previous_application_info.prev_applications_refused,
      previous_application_info.prev_applications_canceled,
      previous_application_info.prev_cash_loan_count,
      previous_application_info.prev_revolving_loan_count,
      previous_application_info.prev_consumer_loan_count,
      previous_application_info.flag_repeater,
      previous_application_info.flag_high_card_user,
      previous_application_info.flag_has_overused_card,
      previous_application_info.max_credit_utilization,
      previous_application_info.avg_credit_utilization,
      previous_application_info.flag_has_had_late_payment,
      previous_application_info.prev_unpaid_amount_for_installments,
      previous_application_info.max_payment_ratio,
      previous_application_info.avg_payment_ratio,
      previous_application_info.flag_has_had_pos_dpd,
      previous_application_info.flag_has_had_pos_severe_dpd,
      previous_application_info.pos_total_dpd,
      previous_application_info.pos_avg_dpd,
      previous_application_info.prev_recent_application_count,
      previous_application_info.prev_long_term_pay_application,
      previous_application_info.prev_total_application_amt,
      previous_application_info.prev_total_given_credit,
      previous_application_info.prev_avg_given_credit,
      previous_application_info.prev_approved_credit_ratio,
      previous_application_info.prev_goods_vs_application_ratio
       
FROM silver.applications

LEFT JOIN bureau_info
ON applications.sk_id_curr = bureau_info.sk_id_curr

LEFT JOIN previous_application_info
ON applications.sk_id_curr = previous_application_info.sk_id_curr
;