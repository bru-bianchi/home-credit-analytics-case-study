CREATE OR REPLACE TABLE silver.previous_application_agg AS

-- Uma linha por sk_id_prev
WITH installments_agg AS (
    SELECT sk_id_prev,

        -- Flags
        MAX(flag_late_payment) AS flag_installment_late_payment,
        MAX(flag_partial_payment) AS flag_installment_partial_payment,

        -- Cálculos
        COUNT(*) AS total_installments,

        AVG(days_late) AS installment_avg_days_late,
        MAX(days_late) AS installment_max_days_late,

        AVG(CASE WHEN flag_late_payment THEN 1 ELSE 0 END) AS installment_late_payment_ratio,
        AVG(CASE WHEN flag_partial_payment THEN 1 ELSE 0 END) AS installment_partial_payment_ratio,

        AVG(payment_ratio) AS installment_avg_payment_ratio,
        SUM(unpaid_amount) AS installment_total_unpaid_amount

    FROM silver.installments_payments
    GROUP BY sk_id_prev
),
credit_card_agg AS (
    SELECT sk_id_prev,

        -- Flags
        MAX(flag_high_utilization) AS flag_card_high_utilization,
        MAX(flag_over_utilization) AS flag_card_over_utilization,

        -- Cálculos
        COUNT(*) AS total_credit_card_records,

        SUM(sk_dpd) AS card_total_dpd,
        AVG(sk_dpd) AS card_avg_dpd,

        AVG(credit_utilization_ratio) AS avg_credit_utilization,
        MAX(credit_utilization_ratio) AS max_credit_utilization,

        -- Em quantos meses houveram esses eventos
        COUNT(CASE WHEN flag_high_utilization THEN 1 ELSE 0 END) AS card_high_utilization_count,
        COUNT(CASE WHEN flag_over_utilization THEN 1 ELSE 0 END) AS card_over_utilization_count,
        AVG(CASE WHEN flag_high_utilization THEN 1 ELSE 0 END) AS card_high_utilization_ratio,
        AVG(CASE WHEN flag_over_utilization THEN 1 ELSE 0 END) AS card_over_utilization_ratio,
        AVG(CASE WHEN flag_minimum_payment THEN 1 ELSE 0 END) AS card_minimum_payment_ratio,
        AVG(CASE WHEN flag_cash_advance THEN 1 ELSE 0 END) AS card_cash_advance_ratio

    FROM silver.credit_card_balance
    GROUP BY sk_id_prev
),

pos_cash_agg AS (
    SELECT sk_id_prev,

        -- Flags
        MAX(flag_has_dpd) AS flag_pos_dpd,
        MAX(flag_severe_dpd) AS flag_pos_severe_dpd,

        -- Cálculos
        COUNT(*) AS total_pos_cash_records,

        AVG(CASE WHEN flag_has_dpd THEN 1 ELSE 0 END) AS pos_dpd_ratio,
        AVG(CASE WHEN flag_severe_dpd THEN 1 ELSE 0 END) AS pos_severe_dpd_ratio,

        SUM(sk_dpd) AS pos_total_dpd,
        AVG(sk_dpd) AS pos_avg_dpd

    FROM silver.pos_cash_balance
    GROUP BY sk_id_prev
)

SELECT pa.*,

    case when ia.sk_id_prev is null then true else false end as flag_installments_info_missing,
    case when cca.sk_id_prev is null then true else false end as flag_credit_card_info_missing,
    case when pca.sk_id_prev is null then true else false end as flag_pos_info_missing,

    -- installments
    ia.flag_installment_late_payment,
    ia.flag_installment_partial_payment,
    ia.total_installments,
    ia.installment_avg_days_late,
    ia.installment_max_days_late,
    ia.installment_late_payment_ratio,
    ia.installment_partial_payment_ratio,
    ia.installment_avg_payment_ratio,
    ia.installment_total_unpaid_amount,

    -- credit card
    cca.flag_card_high_utilization,
    cca.flag_card_over_utilization,
    cca.total_credit_card_records,
    cca.card_total_dpd,
    cca.card_avg_dpd,
    cca.avg_credit_utilization,
    cca.max_credit_utilization,
    cca.card_high_utilization_count,
    cca.card_over_utilization_count,
    cca.card_high_utilization_ratio,
    cca.card_over_utilization_ratio,
    cca.card_minimum_payment_ratio,
    cca.card_cash_advance_ratio,

    -- pos cash
    pca.flag_pos_dpd,
    pca.flag_pos_severe_dpd,
    pca.total_pos_cash_records,
    pca.pos_dpd_ratio,
    pca.pos_severe_dpd_ratio,
    pca.pos_total_dpd,
    pca.pos_avg_dpd

FROM silver.previous_application pa

LEFT JOIN installments_agg ia
    ON pa.sk_id_prev = ia.sk_id_prev

LEFT JOIN credit_card_agg cca
    ON pa.sk_id_prev = cca.sk_id_prev

LEFT JOIN pos_cash_agg pca
    ON pa.sk_id_prev = pca.sk_id_prev
;