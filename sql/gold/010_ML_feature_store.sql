-- Feature store enxuta para modelagem de inadimplência
-- Granularidade: uma linha por sk_id_curr
-- Label de treino: target. Linhas de teste ficam marcadas por flag_test
-- Fontes permitidas: somente tabelas Silver já curadas

CREATE OR REPLACE TABLE gold.credit_risk_feature_store AS

WITH external_credit_features AS (
    SELECT
        sk_id_curr,

        COUNT(*) AS bureau_total_loans,
        SUM(CASE WHEN flag_active_credit THEN 1 ELSE 0 END) AS bureau_active_loans,
        SUM(CASE WHEN flag_bad_debt THEN 1 ELSE 0 END) AS bureau_bad_debt_loans,
        SUM(CASE WHEN flag_credit_was_prolonged THEN 1 ELSE 0 END) AS bureau_prolonged_loans,

        SUM(CASE WHEN flag_consumer_credit THEN 1 ELSE 0 END) AS bureau_consumer_credit_loans,
        SUM(CASE WHEN flag_credit_card THEN 1 ELSE 0 END) AS bureau_credit_card_loans,
        SUM(CASE WHEN flag_car_loan THEN 1 ELSE 0 END) AS bureau_car_loans,
        SUM(CASE WHEN flag_mortgage THEN 1 ELSE 0 END) AS bureau_mortgage_loans,

        AVG(amt_credit_sum) AS bureau_avg_credit,
        MAX(amt_credit_sum) AS bureau_max_credit,
        AVG(amt_credit_sum_debt) AS bureau_avg_debt,
        MAX(amt_credit_sum_debt) AS bureau_max_debt,
        SUM(amt_credit_sum_overdue) AS bureau_total_overdue_amount,
        MAX(amt_credit_sum_overdue) AS bureau_max_overdue_amount,

        SUM(CASE WHEN flag_has_dpd_agg THEN 1 ELSE 0 END) AS bureau_total_loans_with_dpd,
        SUM(CASE WHEN flag_severe_dpd_agg THEN 1 ELSE 0 END) AS bureau_total_loans_with_severe_dpd,
        SUM(CASE WHEN flag_has_recent_dpd THEN 1 ELSE 0 END) AS bureau_total_loans_with_recent_dpd,
        SUM(CASE WHEN flag_recent_credit THEN 1 ELSE 0 END) AS bureau_recent_credit_count,

        AVG(overdue_credit_ratio) AS bureau_avg_overdue_credit_ratio,
        MAX(overdue_credit_ratio) AS bureau_max_overdue_credit_ratio,
        AVG(debt_credit_ratio) AS bureau_avg_debt_credit_ratio,
        MAX(debt_credit_ratio) AS bureau_max_debt_credit_ratio,

        AVG(credit_age_days) AS bureau_avg_credit_age_days,
        MIN(credit_age_days) AS bureau_min_credit_age_days

    FROM silver.agg_bureau_external_credit_behavior
    GROUP BY sk_id_curr
),

internal_credit_features AS (
    SELECT
        sk_id_curr,

        COUNT(*) AS prev_applications_total,
        AVG(CASE WHEN flag_approved_application THEN 1.0 ELSE 0.0 END) AS prev_approval_rate,
        AVG(CASE WHEN flag_refused_application THEN 1.0 ELSE 0.0 END) AS prev_refusal_rate,
        AVG(CASE WHEN flag_canceled_application THEN 1.0 ELSE 0.0 END) AS prev_cancel_rate,

        AVG(CASE WHEN flag_cash_loan THEN 1.0 ELSE 0.0 END) AS prev_cash_loan_rate,
        AVG(CASE WHEN flag_revolving_loan THEN 1.0 ELSE 0.0 END) AS prev_revolving_loan_rate,
        AVG(CASE WHEN flag_consumer_loan THEN 1.0 ELSE 0.0 END) AS prev_consumer_loan_rate,

        MAX(flag_repeater) AS flag_repeater,
        AVG(CASE WHEN flag_recent_application THEN 1.0 ELSE 0.0 END) AS prev_recent_application_rate,
        AVG(CASE WHEN flag_long_term_payment THEN 1.0 ELSE 0.0 END) AS prev_long_term_payment_rate,

        AVG(amt_application) AS prev_avg_application_amt,
        MAX(amt_application) AS prev_max_application_amt,
        AVG(amt_credit) AS prev_avg_given_credit,
        MAX(amt_credit) AS prev_max_given_credit,
        AVG(amt_down_payment) AS prev_avg_down_payment,
        AVG(amt_goods_price) AS prev_avg_goods_price,
        AVG(cnt_payment) AS prev_avg_cnt_payment,
        MAX(cnt_payment) AS prev_max_cnt_payment,
        AVG(ABS(days_decision)) AS prev_avg_days_since_decision,
        MIN(ABS(days_decision)) AS prev_min_days_since_decision,

        AVG(approved_credit_ratio) AS prev_avg_approved_credit_ratio,
        AVG(annuity_credit_ratio) AS prev_avg_annuity_credit_ratio,
        AVG(goods_vs_application_ratio) AS prev_avg_goods_vs_application_ratio,

        AVG(CASE WHEN NOT flag_installments_info_missing THEN 1.0 ELSE 0.0 END) AS prev_installments_available_rate,
        AVG(CASE WHEN NOT flag_credit_card_info_missing THEN 1.0 ELSE 0.0 END) AS prev_credit_card_available_rate,
        AVG(CASE WHEN NOT flag_pos_info_missing THEN 1.0 ELSE 0.0 END) AS prev_pos_available_rate,

        MAX(flag_installment_late_payment) AS flag_has_had_late_payment,
        MAX(flag_installment_partial_payment) AS flag_has_had_partial_payment,
        SUM(total_installments) AS prev_total_installments,
        AVG(installment_avg_days_late) AS prev_avg_days_late_installments,
        MAX(installment_max_days_late) AS prev_max_days_late_installments,
        SUM(installment_total_unpaid_amount) AS prev_unpaid_amount_for_installments,
        MAX(max_payment_ratio) AS max_payment_ratio,
        AVG(installment_late_payment_ratio) AS prev_avg_late_payment_ratio,
        AVG(installment_partial_payment_ratio) AS prev_avg_partial_payment_ratio,
        AVG(wavg_payment_ratio) AS avg_payment_ratio,

        MAX(flag_pos_dpd) AS flag_has_had_pos_dpd,
        MAX(flag_pos_severe_dpd) AS flag_has_had_pos_severe_dpd,
        AVG(pos_dpd_ratio) AS prev_avg_pos_dpd_ratio,
        AVG(pos_severe_dpd_ratio) AS prev_avg_pos_severe_dpd_ratio,
        AVG(pos_avg_dpd) AS pos_avg_dpd

    FROM silver.agg_internal_historical_behavior
    GROUP BY sk_id_curr
)

SELECT
    applications.sk_id_curr,
    applications.target,
    applications.flag_test,

    applications.flag_cash_loan,
    applications.flag_revolving_loan,
    applications.flag_consumer_loan,
    applications.amt_income_total,
    applications.amt_credit,
    applications.amt_annuity,
    applications.amt_goods_price,
    applications.annuity_credit_ratio,
    applications.loan_income_ratio,
    applications.annuity_income_ratio,
    applications.debt_good_ratio,
    applications.income_per_person,

    (applications.code_gender = 'F') AS flag_gender_female,
    (applications.code_gender = 'M') AS flag_gender_male,
    applications.cnt_children,
    applications.cnt_fam_members,
    applications.age_years,
    applications.employment_years,

    (applications.name_income_type = 'Working') AS flag_income_working,
    (applications.name_income_type = 'Commercial associate') AS flag_income_commercial_associate,
    (applications.name_income_type = 'Pensioner') AS flag_income_pensioner,
    (applications.name_income_type = 'State servant') AS flag_income_state_servant,
    applications.flag_employed,
    applications.flag_employment_missing,
    applications.flag_economically_inactive,
    applications.flag_self_employed,
    applications.flag_unemployed,
    applications.flag_student,

    (applications.name_education_type = 'Secondary / secondary special') AS flag_education_secondary,
    (applications.name_education_type = 'Higher education') AS flag_education_higher,
    (applications.name_education_type = 'Incomplete higher') AS flag_education_incomplete_higher,
    (applications.name_education_type = 'Lower secondary') AS flag_education_lower_secondary,
    (applications.name_education_type = 'Academic degree') AS flag_education_academic_degree,

    applications.flag_married,
    (applications.name_family_status = 'Single / not married') AS flag_family_single,
    (applications.name_family_status = 'Civil marriage') AS flag_family_civil_marriage,
    (applications.name_family_status = 'Separated') AS flag_family_separated,
    (applications.name_family_status = 'Widow') AS flag_family_widow,

    (applications.name_housing_type = 'House / apartment') AS flag_housing_house_apartment,
    (applications.name_housing_type = 'With parents') AS flag_housing_with_parents,
    (applications.name_housing_type = 'Municipal apartment') AS flag_housing_municipal,
    (applications.name_housing_type = 'Rented apartment') AS flag_housing_rented,

    (applications.occupation_type_clean = 'Unknown') AS flag_occupation_unknown,
    (applications.occupation_type_clean = 'Laborers') AS flag_occupation_laborers,
    (applications.occupation_type_clean = 'Sales staff') AS flag_occupation_sales_staff,
    (applications.occupation_type_clean = 'Core staff') AS flag_occupation_core_staff,
    (applications.occupation_type_clean = 'Managers') AS flag_occupation_managers,
    (applications.occupation_type_clean = 'Drivers') AS flag_occupation_drivers,
    (applications.occupation_type_clean = 'High skill tech staff') AS flag_occupation_high_skill_tech,
    (applications.occupation_type_clean = 'Accountants') AS flag_occupation_accountants,
    (applications.occupation_type_clean = 'Security staff') AS flag_occupation_security_staff,

    applications.flag_own_car,
    applications.flag_car_age_missing,
    applications.flag_own_realty,

    applications.weekday_appr_process_start,
    applications.hour_appr_process_start,
    applications.days_registration,
    applications.days_id_publish,
    applications.days_last_phone_change,
    applications.region_population_relative,
    applications.region_rating_client,
    applications.region_rating_client_w_city,
    applications.reg_region_not_live_region,
    applications.reg_region_not_work_region,
    applications.live_region_not_work_region,
    applications.reg_city_not_live_city,
    applications.reg_city_not_work_city,
    applications.live_city_not_work_city,

    applications.flag_ext_source_1_missing,
    applications.flag_ext_source_2_missing,
    applications.flag_ext_source_3_missing,
    applications.ext_source_count,
    applications.ext_source_mean,
    applications.ext_source_max,
    applications.ext_source_min,
    applications.total_credit_inquiries,
    applications.def_30_cnt_social_circle,
    applications.def_60_cnt_social_circle,
    applications.flag_has_social_default,
    applications.flag_social_default_na,

    applications.housing_info_fill_rate,
    applications.contact_info_filled_rate,
    applications.core_profile_info_filled_rate,
    applications.ext_source_missing_count,
    applications.ext_source_fill_rate,
    applications.credit_bureau_request_info_filled_rate,
    applications.social_circle_info_filled_rate,
    applications.document_provided_rate,
    applications.cadastral_completeness_rate,

    (external_credit_features.sk_id_curr IS NULL) AS flag_missing_bureau_info,
    external_credit_features.bureau_total_loans,
    external_credit_features.bureau_active_loans,
    external_credit_features.bureau_bad_debt_loans,
    external_credit_features.bureau_prolonged_loans,
    external_credit_features.bureau_consumer_credit_loans,
    external_credit_features.bureau_credit_card_loans,
    external_credit_features.bureau_car_loans,
    external_credit_features.bureau_mortgage_loans,
    external_credit_features.bureau_avg_credit,
    external_credit_features.bureau_max_credit,
    external_credit_features.bureau_avg_debt,
    external_credit_features.bureau_max_debt,
    external_credit_features.bureau_total_overdue_amount,
    external_credit_features.bureau_max_overdue_amount,
    external_credit_features.bureau_total_loans_with_dpd,
    external_credit_features.bureau_total_loans_with_severe_dpd,
    external_credit_features.bureau_total_loans_with_recent_dpd,
    external_credit_features.bureau_recent_credit_count,
    external_credit_features.bureau_avg_overdue_credit_ratio,
    external_credit_features.bureau_max_overdue_credit_ratio,
    external_credit_features.bureau_avg_debt_credit_ratio,
    external_credit_features.bureau_max_debt_credit_ratio,
    external_credit_features.bureau_avg_credit_age_days,
    external_credit_features.bureau_min_credit_age_days,

    (internal_credit_features.sk_id_curr IS NULL) AS flag_missing_prev_applications_info,
    internal_credit_features.prev_applications_total,
    internal_credit_features.prev_approval_rate,
    internal_credit_features.prev_refusal_rate,
    internal_credit_features.prev_cancel_rate,
    internal_credit_features.prev_cash_loan_rate,
    internal_credit_features.prev_revolving_loan_rate,
    internal_credit_features.prev_consumer_loan_rate,
    internal_credit_features.flag_repeater,
    internal_credit_features.prev_recent_application_rate,
    internal_credit_features.prev_long_term_payment_rate,
    internal_credit_features.prev_avg_application_amt,
    internal_credit_features.prev_max_application_amt,
    internal_credit_features.prev_avg_given_credit,
    internal_credit_features.prev_max_given_credit,
    internal_credit_features.prev_avg_down_payment,
    internal_credit_features.prev_avg_goods_price,
    internal_credit_features.prev_avg_cnt_payment,
    internal_credit_features.prev_max_cnt_payment,
    internal_credit_features.prev_avg_days_since_decision,
    internal_credit_features.prev_min_days_since_decision,
    internal_credit_features.prev_avg_approved_credit_ratio,
    internal_credit_features.prev_avg_annuity_credit_ratio,
    internal_credit_features.prev_avg_goods_vs_application_ratio,
    internal_credit_features.prev_installments_available_rate,
    internal_credit_features.prev_credit_card_available_rate,
    internal_credit_features.prev_pos_available_rate,
    internal_credit_features.flag_has_had_late_payment,
    internal_credit_features.flag_has_had_partial_payment,
    internal_credit_features.prev_total_installments,
    internal_credit_features.prev_avg_days_late_installments,
    internal_credit_features.prev_max_days_late_installments,
    internal_credit_features.prev_unpaid_amount_for_installments,
    internal_credit_features.max_payment_ratio,
    internal_credit_features.prev_avg_late_payment_ratio,
    internal_credit_features.prev_avg_partial_payment_ratio,
    internal_credit_features.avg_payment_ratio,
    internal_credit_features.flag_has_had_pos_dpd,
    internal_credit_features.flag_has_had_pos_severe_dpd,
    internal_credit_features.prev_avg_pos_dpd_ratio,
    internal_credit_features.prev_avg_pos_severe_dpd_ratio,
    internal_credit_features.pos_avg_dpd

FROM silver.applications AS applications

LEFT JOIN external_credit_features
    ON applications.sk_id_curr = external_credit_features.sk_id_curr

LEFT JOIN internal_credit_features
    ON applications.sk_id_curr = internal_credit_features.sk_id_curr
;
