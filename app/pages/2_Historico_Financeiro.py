from __future__ import annotations

import plotly.express as px
import streamlit as st

from lib.db import DEFAULT_WAREHOUSE_PATH, query_df, table_exists


st.set_page_config(page_title="Historico Financeiro | Credit Risk", layout="wide")

st.title("Historico Financeiro PLACEHOLDER")

#
# def format_number(value: float | int | None) -> str:
#     if value is None:
#         return "-"
#     return f"{value:,.0f}"
#
#
# def format_currency(value: float | int | None) -> str:
#     if value is None:
#         return "-"
#     return f"R$ {value:,.0f}"
#
#
# def format_percent(value: float | int | None) -> str:
#     if value is None:
#         return "-"
#     return f"{value:.2%}"
#
#
# st.title("Historico financeiro")
#
# warehouse_path = st.sidebar.text_input("DuckDB warehouse", value=str(DEFAULT_WAREHOUSE_PATH))
# min_clients = st.sidebar.number_input("Minimo de clientes por grupo", min_value=1, value=500, step=100)
# top_n = st.sidebar.slider("Top drivers por lift", min_value=5, max_value=30, value=15, step=5)
#
# required_tables = [
#     ("gold", "fact_credit_risk"),
#     ("gold", "dim_risk_segment"),
# ]
# missing_tables = [
#     f"{schema}.{table}"
#     for schema, table in required_tables
#     if not table_exists(schema, table, warehouse_path)
# ]
#
# if missing_tables:
#     st.warning("Tabelas ausentes: " + ", ".join(missing_tables))
#     st.stop()
#
# summary = query_df(
#     """
#     SELECT
#         COUNT(DISTINCT sk_id_curr) AS clients,
#         AVG(CAST(target AS INTEGER)) AS default_rate,
#         AVG(bureau_total_loans) AS avg_bureau_loans,
#         AVG(prev_applications_total) AS avg_prev_applications,
#         SUM(prev_applications_refused) / NULLIF(SUM(prev_applications_total), 0) AS historical_refusal_rate,
#         SUM(bureau_total_overdue_amount) AS bureau_overdue_amount,
#         SUM(prev_unpaid_amount_for_installments) AS unpaid_installment_amount,
#         AVG(max_credit_utilization) AS avg_max_credit_utilization
#     FROM gold.fact_credit_risk
#     """,
#     warehouse_path,
# ).iloc[0]
#
# metric_cols = st.columns(4)
# metric_cols[0].metric("Clientes", format_number(summary["clients"]))
# metric_cols[1].metric("Taxa de inadimplencia", format_percent(summary["default_rate"]))
# metric_cols[2].metric("Creditos antigos medios", format_number(summary["avg_bureau_loans"]))
# metric_cols[3].metric("Solicitacoes historicas medias", format_number(summary["avg_prev_applications"]))
#
# metric_cols = st.columns(4)
# metric_cols[0].metric("Taxa recusa historica", format_percent(summary["historical_refusal_rate"]))
# metric_cols[1].metric("Atraso externo aberto", format_currency(summary["bureau_overdue_amount"]))
# metric_cols[2].metric("Parcelas historicas em atraso", format_currency(summary["unpaid_installment_amount"]))
# metric_cols[3].metric("Utilizacao maxima cartao", format_percent(summary["avg_max_credit_utilization"]))
#
# drivers = query_df(
#     """
#     WITH base AS (
#         SELECT
#             f.sk_id_curr,
#             f.target,
#             f.amt_credit,
#             f.bureau_total_loans,
#             f.bureau_active_loans,
#             f.bureau_bad_debt_loans,
#             f.bureau_total_loans_with_dpd,
#             f.bureau_total_loans_with_severe_dpd,
#             f.bureau_total_overdue_amount,
#             f.bureau_max_dpd_status,
#             f.prev_applications_total,
#             f.prev_applications_refused,
#             f.prev_applications_approved,
#             f.max_credit_utilization,
#             f.avg_credit_utilization,
#             f.prev_unpaid_amount_for_installments,
#             f.pos_total_dpd,
#             rs.flag_high_card_user,
#             rs.flag_has_overused_card,
#             rs.flag_has_had_late_payment,
#             rs.internal_pos_dpd,
#             rs.internal_pos_severe_dpd,
#             rs.external_had_dpd,
#             rs.external_severe_dpd,
#             rs.external_bad_debt,
#             rs.external_recent_credit
#         FROM gold.fact_credit_risk f
#         LEFT JOIN gold.dim_risk_segment rs
#             ON f.risk_segment_key = rs.risk_segment_key
#     ),
#     portfolio AS (
#         SELECT AVG(CAST(target AS INTEGER)) AS portfolio_default_rate
#         FROM base
#     ),
#     driver_rows AS (
#         SELECT
#             'Historico atraso externo' AS driver,
#             CASE WHEN external_had_dpd THEN 'Com DPD' ELSE 'Sem DPD' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Atraso externo severo' AS driver,
#             CASE WHEN external_severe_dpd THEN 'Severo' ELSE 'Nao severo' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Bad debt externo' AS driver,
#             CASE WHEN external_bad_debt THEN 'Com bad debt' ELSE 'Sem bad debt' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Atraso interno em parcela' AS driver,
#             CASE WHEN flag_has_had_late_payment THEN 'Teve atraso' ELSE 'Sem atraso' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'POS DPD interno' AS driver,
#             CASE WHEN internal_pos_dpd THEN 'Com DPD' ELSE 'Sem DPD' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'POS DPD severo' AS driver,
#             CASE WHEN internal_pos_severe_dpd THEN 'Severo' ELSE 'Nao severo' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Uso alto de cartao' AS driver,
#             CASE WHEN flag_high_card_user THEN 'High user' ELSE 'Nao high user' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Overuse de cartao' AS driver,
#             CASE WHEN flag_has_overused_card THEN 'Overuser' ELSE 'Nao overuser' END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Quantidade de creditos antigos' AS driver,
#             CASE
#                 WHEN bureau_total_loans IS NULL THEN 'Unknown'
#                 WHEN bureau_total_loans = 0 THEN '0'
#                 WHEN bureau_total_loans <= 2 THEN '1-2'
#                 WHEN bureau_total_loans <= 5 THEN '3-5'
#                 ELSE '6+'
#             END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Emprestimos recusados historicos' AS driver,
#             CASE
#                 WHEN prev_applications_refused IS NULL THEN 'Unknown'
#                 WHEN prev_applications_refused = 0 THEN '0'
#                 WHEN prev_applications_refused <= 2 THEN '1-2'
#                 WHEN prev_applications_refused <= 5 THEN '3-5'
#                 ELSE '6+'
#             END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Solicitacoes antigas' AS driver,
#             CASE
#                 WHEN prev_applications_total IS NULL THEN 'Unknown'
#                 WHEN prev_applications_total = 0 THEN '0'
#                 WHEN prev_applications_total <= 2 THEN '1-2'
#                 WHEN prev_applications_total <= 5 THEN '3-5'
#                 ELSE '6+'
#             END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Utilizacao maxima do cartao' AS driver,
#             CASE
#                 WHEN max_credit_utilization IS NULL THEN 'Unknown'
#                 WHEN max_credit_utilization < 0.30 THEN '<30%'
#                 WHEN max_credit_utilization < 0.70 THEN '30%-69%'
#                 WHEN max_credit_utilization <= 1.00 THEN '70%-100%'
#                 ELSE '>100%'
#             END AS driver_value,
#             *
#         FROM base
#         UNION ALL
#         SELECT
#             'Status DPD maximo externo' AS driver,
#             CASE
#                 WHEN bureau_max_dpd_status IS NULL THEN 'Unknown'
#                 WHEN bureau_max_dpd_status = 0 THEN '0'
#                 WHEN bureau_max_dpd_status <= 2 THEN '1-2'
#                 WHEN bureau_max_dpd_status <= 4 THEN '3-4'
#                 ELSE '5+'
#             END AS driver_value,
#             *
#         FROM base
#     )
#     SELECT
#         driver,
#         driver_value,
#         COUNT(DISTINCT sk_id_curr) AS clients,
#         AVG(CAST(target AS INTEGER)) AS default_rate,
#         AVG(CAST(target AS INTEGER)) - MAX(portfolio.portfolio_default_rate) AS default_rate_lift,
#         SUM(amt_credit) AS credit_amount,
#         SUM(CASE WHEN target THEN amt_credit ELSE 0 END) AS default_credit_amount,
#         SUM(bureau_total_overdue_amount) AS bureau_overdue_amount,
#         SUM(prev_unpaid_amount_for_installments) AS unpaid_installment_amount,
#         AVG(bureau_total_loans) AS avg_bureau_loans,
#         AVG(prev_applications_refused) AS avg_prev_refused,
#         AVG(max_credit_utilization) AS avg_max_credit_utilization
#     FROM driver_rows
#     CROSS JOIN portfolio
#     GROUP BY 1, 2
#     HAVING COUNT(DISTINCT sk_id_curr) >= ?
#     ORDER BY default_rate_lift DESC NULLS LAST, clients DESC
#     """,
#     warehouse_path,
#     [min_clients],
# )
#
# st.subheader("Drivers de inadimplencia no historico financeiro")
#
# top_drivers = drivers.head(top_n).copy()
# top_drivers["driver_label"] = top_drivers["driver"] + " | " + top_drivers["driver_value"].astype(str)
#
# fig = px.bar(
#     top_drivers,
#     x="default_rate_lift",
#     y="driver_label",
#     color="driver",
#     orientation="h",
#     labels={"default_rate_lift": "Lift vs carteira", "driver_label": "Driver"},
# )
# fig.update_layout(xaxis_tickformat=".1%", yaxis={"categoryorder": "total ascending"})
# st.plotly_chart(fig, use_container_width=True)
#
# selected_driver = st.selectbox("Detalhar driver", drivers["driver"].drop_duplicates().tolist())
# selected = drivers[drivers["driver"] == selected_driver].copy()
#
# left, right = st.columns([2, 1])
#
# with left:
#     fig = px.bar(
#         selected,
#         x="driver_value",
#         y="default_rate",
#         color="clients",
#         text="default_rate",
#         labels={
#             "driver_value": selected_driver,
#             "default_rate": "Taxa de inadimplencia",
#             "clients": "Clientes",
#         },
#     )
#     fig.update_traces(texttemplate="%{text:.2%}", textposition="outside")
#     fig.update_layout(yaxis_tickformat=".1%", xaxis_tickangle=-30, showlegend=False)
#     st.plotly_chart(fig, use_container_width=True)
#
# with right:
#     st.dataframe(selected, use_container_width=True, hide_index=True)
#
# st.subheader("Tabela consolidada")
# st.dataframe(drivers, use_container_width=True, hide_index=True)
