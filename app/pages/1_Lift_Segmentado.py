from __future__ import annotations

import plotly.express as px
import streamlit as st
from annotated_text import annotated_text
import matplotlib as plt

from lib.db import DEFAULT_WAREHOUSE_PATH, describe_data_source, list_gold_tables, query_df, table_exists

st.set_page_config(
    page_title="Dashboard Inadimplência",
    layout="wide",
)


def format_number(value: float | int | None) -> str:
    if value is None:
        return "-"
    elif value >= 1_000_000_000.0:
        return f"{value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000.0:
        return f"{value / 1_000_000:.1f}M"
    return f"{value:,.0f}"


def format_currency(value: float | int | None) -> str:
    if value is None:
        return "-"
    return "R$ " + format_number(value)


def format_percent(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}"


st.title("Lift de Risco Segmentado")

warehouse_path = DEFAULT_WAREHOUSE_PATH
st.sidebar.caption(describe_data_source(warehouse_path))

try:
    gold_tables = list_gold_tables(warehouse_path)
except Exception as exc:
    st.error(
        "Nao foi possível conectar às tabelas Gold. Verifique as variáveis MOTHERDUCK_TOKEN/MOTHERDUCK_DATABASE "
        "ou o warehouse local em app/lib/db.py."
    )
    st.exception(exc)
    st.stop()

required_tables = [
    ("gold", "fact_credit_risk"),
    ("gold", "dim_requester"),
    ("gold", "dim_contract"),
    ("gold", "dim_risk_segment"),
    ("gold", "ref_band_rules"),
]
missing_tables = [
    f"{schema}.{table}"
    for schema, table in required_tables
    if not table_exists(schema, table, warehouse_path)
]

if missing_tables:
    st.warning("Tabelas ausentes: " + ", ".join(missing_tables))
    st.subheader("Objetos Gold disponíveis")
    st.dataframe(gold_tables, use_container_width=True, hide_index=True)
    st.stop()

# Ordem das faixas categóricas
bands = query_df(
    """
    SELECT band_group, band_order, band_label
    FROM gold.ref_band_rules
    WHERE band_label not in ('Unknown', 'Outlier')
    """,
    warehouse_path
)

income_order = bands[bands["band_group"] == "income_band"]["band_label"].drop_duplicates().tolist()
annuity_order = bands[bands["band_group"] == "annuity_income_band"]["band_label"].drop_duplicates().tolist()

# Resumo
summary = query_df(
    """
    SELECT COUNT(DISTINCT sk_id_curr)                                                AS n_total_loans,
           SUM(amt_credit)                                                           AS total_credit_amount,
           AVG(CAST(target AS INTEGER))                                              AS default_rate,
           SUM(CASE WHEN target THEN 1 ELSE 0 END)                                   AS total_defaults,
           SUM(CASE WHEN target THEN amt_credit ELSE 0 END)                          AS default_credit_amount,
           SUM(prev_applications_approved) / NULLIF(SUM(prev_applications_total), 0) AS historical_approval_rate
    FROM gold.fact_credit_risk
    """,
    warehouse_path,
).iloc[0]

st.subheader("Lift de Inadimplência por DTI e Faixa Salarial")
st.markdown("""
    O DTI (Debt to Income) é um indicador que mede o quanto da renda de uma pessoa já está comprometida com dívidas. 
    
    Na nossa análise, ela é calculada pela *proxy* **Annuity / Income**, e é dividida nas seguintes faixas:
    
    - Risco Baixo: até 35%
    - Risco Moderado: de 36% a 41%
    - Risco Alto: de 42% a 50%
    - Risco Muito Alto: acima de 51%
    
    Esses índices foram definidos usando as faixas do [Navy Federal](https://www.navyfederal.org/makingcents/credit-debt/debt-to-income-ratio.html) como referência.
""")

cross_annuity_income = query_df(
    """
        WITH portfolio AS (
            SELECT AVG(CAST(target AS INTEGER)) AS baseline_default_rate
            FROM gold.fact_credit_risk
        )
        SELECT 
            dim_requester.income_band,
            dim_risk_segment.annuity_income_band,
            AVG(CASE WHEN fact.target THEN 1 ELSE 0 END)
                / NULLIF(MAX(portfolio.baseline_default_rate), 0) AS lift_inadimplencia
        FROM gold.fact_credit_risk AS fact
        CROSS JOIN portfolio
        LEFT JOIN gold.dim_requester 
            ON fact.requester_key = dim_requester.requester_key
        LEFT JOIN gold.dim_risk_segment 
            ON fact.risk_segment_key = dim_risk_segment.risk_segment_key
        WHERE dim_risk_segment.annuity_income_band NOT IN ('Unknown','Outlier')
        GROUP BY 1, 2
        ORDER BY 1, 2
    """,
    warehouse_path,
)

pivoted = (
    cross_annuity_income
    .pivot(
        index="income_band",
        columns="annuity_income_band",
        values="lift_inadimplencia",
    )
)

pivoted = pivoted.reindex(index=income_order, columns=annuity_order).rename_axis("Faixa Salarial x DTI")
pivoted = pivoted.style.background_gradient(cmap='RdYlGn_r').format("{:.2f}x")

st.dataframe(pivoted)

st.info("""

    ### Insight

    O grupo :orange-badge[Risco Alto com salário anual de < 90k] é o grupo com maior lift da carteira hoje, 
    seguido imediatamente pelo :orange-badge[Risco Médio com salário anual de < 90k].
    """
        )

st.divider()

st.subheader("Como comportamento observado muda o risco")
st.caption(
    "Essa sessão informa qual o lift de risco (% de inadimplência a mais) de perfis de comportamento (ex: high-user de cartão) comparado com o baseline da carteira geral.")
st.caption("Representatividade = % dentro do grupo de inadimplentes (target = 1)")

min_clients = st.sidebar.number_input(
    "Mínimo de clientes por perfil",
    min_value=100,
    value=1000,
    step=100,
)
min_credit_amount = st.sidebar.number_input(
    "Volume de crédito mínimo por perfil (R$)",
    min_value=0,
    value=50_000_000,
    step=10_000_000,
)

flag_metrics = query_df(
    """
    WITH base AS (SELECT fact.sk_id_curr,
                         fact.target,
                         fact.amt_credit,
                         fact.amt_income_total,
                         fact.annuity_income_ratio,
                         fact.loan_income_ratio,
                         fact.total_credit_inquiries,
                         fact.bureau_total_loans,
                         fact.bureau_total_loans_with_dpd,
                         fact.bureau_total_loans_with_severe_dpd,
                         fact.bureau_total_overdue_amount,
                         fact.prev_applications_refused,
                         fact.max_credit_utilization,
                         fact.contact_info_filled_rate,
                         fact.document_provided_rate,
                         fact.housing_info_fill_rate,
                         fact.contact_info_filled_rate,
                         fact.ext_source_fill_rate,
                         requester.flag_self_employed,
                         requester.flag_unemployed,
                         requester.flag_economically_inactive,
                         requester.flag_pensioner,
                         requester.flag_own_car,
                         requester.flag_own_realty,
                         risk.flag_high_card_user,
                         risk.flag_has_overused_card,
                         risk.flag_has_had_late_payment,
                         risk.internal_pos_dpd,
                         risk.internal_pos_severe_dpd,
                         risk.external_had_dpd,
                         risk.external_severe_dpd,
                         risk.external_bad_debt,
                         risk.external_recent_credit,
                         risk.flag_missing_prev_applications_info,
                         risk.flag_missing_bureau_info
                  FROM gold.fact_credit_risk AS fact
                           LEFT JOIN gold.dim_requester AS requester
                                     ON fact.requester_key = requester.requester_key

                           LEFT JOIN gold.dim_risk_segment AS risk
                                     ON fact.risk_segment_key = risk.risk_segment_key),
         portfolio AS (SELECT COUNT(DISTINCT sk_id_curr)              AS portfolio_clients,
                              SUM(CASE WHEN target THEN 1 ELSE 0 END) AS portfolio_defaults,
                              SUM(amt_credit)                         AS portfolio_credit_amount,
                              AVG(CAST(target AS INTEGER))            AS portfolio_default_rate
                       FROM base),
         flag_rows AS (SELECT 'Self employed' AS segmento, COALESCE(flag_self_employed, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Desempregado' AS segmento, COALESCE(flag_unemployed, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Economicamente inativo'                    AS segmento,
                              COALESCE(flag_economically_inactive, FALSE) AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'Pensionista' AS segmento, COALESCE(flag_pensioner, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Sem carro próprio' AS segmento, NOT COALESCE(flag_own_car, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Sem imóvel próprio' AS segmento, NOT COALESCE(flag_own_realty, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'High user cartão' AS segmento, COALESCE(flag_high_card_user, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Overuser cartão' AS segmento, COALESCE(flag_has_overused_card, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Atraso interno em parcela'                AS segmento,
                              COALESCE(flag_has_had_late_payment, FALSE) AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'DPD interno POS' AS segmento, COALESCE(internal_pos_dpd, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'DPD interno severo'                     AS segmento,
                              COALESCE(internal_pos_severe_dpd, FALSE) AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'DPD externo' AS segmento, COALESCE(external_had_dpd, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'DPD externo severo' AS segmento, COALESCE(external_severe_dpd, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Bad debt externo' AS segmento, COALESCE(external_bad_debt, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Crédito externo recente'               AS segmento,
                              COALESCE(external_recent_credit, FALSE) AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'Sem histórico interno'                              AS segmento,
                              COALESCE(flag_missing_prev_applications_info, FALSE) AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'Sem bureau' AS segmento, COALESCE(flag_missing_bureau_info, FALSE) AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Completude cadastral Residência <70%' AS segmento,
                              housing_info_fill_rate < 0.70          AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'Contato cadastral <70%'                     AS segmento,
                              COALESCE(contact_info_filled_rate, 0) < 0.70 AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'Documentos <70%' AS segmento, COALESCE(document_provided_rate, 0) < 0.70 AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Consultas de crédito 6+'                AS segmento,
                              COALESCE(total_credit_inquiries, 0) >= 6 AS flag_value,
                              *
                       FROM base
                       UNION ALL
                       SELECT 'Créditos antigos 6+' AS segmento, COALESCE(bureau_total_loans, 0) >= 6 AS flag_value, *
                       FROM base
                       UNION ALL
                       SELECT 'Recusas históricas 3+'                     AS segmento,
                              COALESCE(prev_applications_refused, 0) >= 3 AS flag_value,
                              *
                       FROM base)
    SELECT segmento,
           COUNT(DISTINCT sk_id_curr)                                                      AS clientes,
           SUM(CASE WHEN target THEN 1 ELSE 0 END)                                         AS defaults,
           SUM(amt_credit)                                                                 AS valor_emprestimos,
           AVG(CAST(target AS INTEGER))                                                    AS taxa_inadimplencia,
           AVG(CAST(target AS INTEGER)) / NULLIF(MAX(portfolio.portfolio_default_rate), 0) AS lift_risco,
           AVG(CAST(target AS INTEGER)) - MAX(portfolio.portfolio_default_rate)            AS lift_pp,
           COUNT(DISTINCT sk_id_curr)::DOUBLE / NULLIF(MAX(portfolio.portfolio_clients), 0) AS pct_clientes, SUM(CASE WHEN target THEN 1 ELSE 0 END)::DOUBLE / NULLIF(MAX(portfolio.portfolio_defaults), 0) AS pct_defaults,
        SUM(amt_credit) / NULLIF(MAX(portfolio.portfolio_credit_amount), 0) AS pct_valor_emprestimos,
           SUM(CASE WHEN target THEN amt_credit ELSE 0 END)                                AS valor_emprestimos_inadimplentes
    FROM flag_rows
             CROSS JOIN portfolio
    WHERE flag_value
    GROUP BY 1
    HAVING COUNT(DISTINCT sk_id_curr) >= ?
    ORDER BY lift_risco DESC NULLS LAST, defaults DESC, valor_emprestimos DESC
    """,
    warehouse_path,
    [min_clients],
)

left, right = st.columns([2, 1])

with left:
    lift_chart = flag_metrics.sort_values("lift_risco", ascending=False).head(12)
    fig = px.bar(
        lift_chart,
        x="lift_risco",
        y="segmento",
        orientation="h",
        range_x=[0, 2],
        text="lift_risco",
        color="pct_defaults",
        labels={
            "segmento": "Comportamento Observado",
            "lift_risco": "Lift contra baseline da carteira",
            "pct_defaults": "Representatividade",
        },
    )
    fig.add_vline(x=1, line_dash="dash", line_color="#666")
    fig.update_traces(texttemplate="%{text:.2f}x", textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.metric("Baseline da carteira", format_percent(summary["default_rate"]))
    st.metric("Defaults observados", format_number(summary["total_defaults"]))
    st.metric("R$ inadimplente", format_currency(summary["default_credit_amount"]))

st.info("""

    ### Insight
        
    Apesar de clientes com crédito externo recente possuírem um lift maior, o segmento de clientes que tem
    :orange-badge[pouca informação de residência], e aqueles que :orange-badge[possuem atraso interno em parcelas]
    são os grupos  mais representativos entre os inadimplentes.
    """
        )

st.divider()

# st.subheader("Contribuição para inadimplência total")
# contribution = flag_metrics.sort_values("pct_defaults", ascending=False).copy()
# st.dataframe(
#     contribution[
#         [
#             "segmento",
#             "pct_clientes",
#             "pct_defaults",
#             "pct_valor_emprestimos",
#             "taxa_inadimplencia",
#             "lift_risco",
#         ]
#     ].style.format(
#         {
#             "pct_clientes": format_percent,
#             "pct_defaults": format_percent,
#             "pct_valor_emprestimos": format_percent,
#             "taxa_inadimplencia": format_percent,
#             "lift_risco": "{:.2f}x",
#         }
#     ),
#     use_container_width=True,
#     hide_index=True,
# )

st.subheader("Correlação com inadimplência")

correlation = query_df(
    """
    WITH base AS (SELECT CAST(fact.target AS DOUBLE)                                      AS target,
                         fact.amt_income_total,
                         fact.annuity_income_ratio,
                         fact.loan_income_ratio,
                         fact.ext_source_mean,
                         fact.total_credit_inquiries,
                         fact.bureau_total_loans,
                         fact.bureau_total_loans_with_dpd,
                         fact.bureau_total_loans_with_severe_dpd,
                         fact.prev_applications_refused,
                         fact.max_credit_utilization,
                         (
                             COALESCE(fact.housing_info_fill_rate, 0)
                                 + COALESCE(fact.contact_info_filled_rate, 0)
                                 + COALESCE(fact.ext_source_fill_rate, 0)
                                 + COALESCE(fact.social_circle_info_filled_rate, 0)
                                 + COALESCE(fact.document_provided_rate, 0)
                             ) /
                         5                                                                AS cadastral_completeness_rate,
                         CAST(COALESCE(requester.flag_self_employed, FALSE) AS INTEGER)   AS flag_self_employed,
                         CAST(COALESCE(requester.flag_unemployed, FALSE) AS INTEGER)      AS flag_unemployed,
                         CAST(COALESCE(risk.flag_high_card_user, FALSE) AS INTEGER)       AS flag_high_card_user,
                         CAST(COALESCE(risk.flag_has_overused_card, FALSE) AS INTEGER)    AS flag_has_overused_card,
                         CAST(COALESCE(risk.flag_has_had_late_payment, FALSE) AS INTEGER) AS flag_has_had_late_payment,
                         CAST(COALESCE(risk.external_had_dpd, FALSE) AS INTEGER)          AS external_had_dpd,
                         CAST(COALESCE(risk.external_severe_dpd, FALSE) AS INTEGER)       AS external_severe_dpd,
                         CAST(COALESCE(risk.external_bad_debt, FALSE) AS INTEGER)         AS external_bad_debt
                  FROM gold.fact_credit_risk AS fact
                           LEFT JOIN gold.dim_requester AS requester
                                     ON fact.requester_key = requester.requester_key
                           LEFT JOIN gold.dim_risk_segment AS risk
                                     ON fact.risk_segment_key = risk.risk_segment_key)
    SELECT 'Renda' AS variavel, corr(target, amt_income_total) AS correlacao
    FROM base
    UNION ALL
    SELECT 'Anuidade/Renda', corr(target, annuity_income_ratio)
    FROM base
    UNION ALL
    SELECT 'Crédito/Renda', corr(target, loan_income_ratio)
    FROM base
    UNION ALL
    SELECT 'Score externo médio', corr(target, ext_source_mean)
    FROM base
    UNION ALL
    SELECT 'Consultas crédito', corr(target, total_credit_inquiries)
    FROM base
    UNION ALL
    SELECT 'Créditos antigos', corr(target, bureau_total_loans)
    FROM base
    UNION ALL
    SELECT 'Créditos com DPD', corr(target, bureau_total_loans_with_dpd)
    FROM base
    UNION ALL
    SELECT 'Créditos com DPD severo', corr(target, bureau_total_loans_with_severe_dpd)
    FROM base
    UNION ALL
    SELECT 'Recusas históricas', corr(target, prev_applications_refused)
    FROM base
    UNION ALL
    SELECT 'Utilização cartão max', corr(target, max_credit_utilization)
    FROM base
    UNION ALL
    SELECT 'Completude cadastral', corr(target, cadastral_completeness_rate)
    FROM base
    UNION ALL
    SELECT 'Flag self employed', corr(target, flag_self_employed)
    FROM base
    UNION ALL
    SELECT 'Flag desempregado', corr(target, flag_unemployed)
    FROM base
    UNION ALL
    SELECT 'Flag high card user', corr(target, flag_high_card_user)
    FROM base
    UNION ALL
    SELECT 'Flag overuser cartão', corr(target, flag_has_overused_card)
    FROM base
    UNION ALL
    SELECT 'Flag atraso parcela', corr(target, flag_has_had_late_payment)
    FROM base
    UNION ALL
    SELECT 'Flag DPD externo', corr(target, external_had_dpd)
    FROM base
    UNION ALL
    SELECT 'Flag DPD externo severo', corr(target, external_severe_dpd)
    FROM base
    UNION ALL
    SELECT 'Flag bad debt externo', corr(target, external_bad_debt)
    FROM base
    """,
    warehouse_path,
)

correlation = correlation.dropna().sort_values("correlacao", key=lambda col: col.abs(), ascending=False).head(15)
corr_matrix = correlation.set_index("variavel")[["correlacao"]].T
fig = px.imshow(
    corr_matrix,
    color_continuous_scale="RdBu_r",
    zmin=-0.15,
    zmax=0.15,
    aspect="auto",
    labels={"x": "Variável", "y": "", "color": "Correlação"},
)
fig.update_xaxes(tickangle=-35)
st.plotly_chart(fig, use_container_width=True)

st.info("""

    ### Insight

    - ⬇ **Score Externo Médio** -> ⬆ taxa de inadimplência 
    - ⬇ **Utilização do Limite do Cartão Máxima** -> ⬇ taxa de inadimplência 
    """
        )

st.divider()

# st.subheader("Perfil de alto risco")
# high_risk = flag_metrics[
#     (flag_metrics["valor_emprestimos"] >= min_credit_amount)
#     & (flag_metrics["defaults"] >= 30)
#     ].sort_values(
#     ["lift_risco", "defaults", "valor_emprestimos"],
#     ascending=[False, False, False],
# )
#
# st.dataframe(
#     high_risk[
#         [
#             "segmento",
#             "clientes",
#             "defaults",
#             "valor_emprestimos",
#             "taxa_inadimplencia",
#             "lift_risco",
#             "lift_pp",
#             "pct_defaults",
#         ]
#     ].style.format(
#         {
#             "clientes": format_number,
#             "defaults": format_number,
#             "valor_emprestimos": format_currency,
#             "taxa_inadimplencia": format_percent,
#             "lift_risco": "{:.2f}x",
#             "lift_pp": "{:+.2%}",
#             "pct_defaults": format_percent,
#         }
#     ),
#     use_container_width=True,
#     hide_index=True,
# )
