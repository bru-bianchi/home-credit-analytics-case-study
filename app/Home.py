from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd
import altair as alt
from annotated_text import annotated_text

from lib.db import DEFAULT_WAREHOUSE_PATH, describe_data_source, list_gold_tables, query_df, table_exists
from lib.aux_functions import format_number, format_currency, format_percent

st.set_page_config(
    page_title="Dashboard Inadimplência",
    layout="wide",
)

st.title("Visão Geral da Carteira")

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

age_order = bands[bands["band_group"] == "age_band"]["band_label"].drop_duplicates().tolist()
income_order = bands[bands["band_group"] == "income_band"]["band_label"].drop_duplicates().tolist()
annuity_order = bands[bands["band_group"] == "annuity_income_band"]["band_label"].drop_duplicates().tolist()

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

metric_cols = st.columns(4)
metric_cols[0].metric("Empréstimos Ativos", format_number(summary["n_total_loans"]))
metric_cols[1].metric("Empréstimos Ativos (R$)", format_currency(summary["total_credit_amount"]))
metric_cols[2].metric("Baseline de Inadimplência", format_percent(summary["default_rate"]))

def_rate = summary["default_rate"]

df = pd.DataFrame({
    "categoria": ["Valor", "Restante"],
    "valor": [def_rate, 1 - def_rate]
})
base = alt.Chart(df).encode(theta="valor:Q")
donut = base.mark_arc(innerRadius=40)
text = alt.Chart(pd.DataFrame({"text": [format_percent(def_rate)]})).mark_text(size=22, fontWeight="bold").encode(
    text="text:N")
metric_cols[3].altair_chart((donut + text).properties(width=120, height=120), use_container_width=False)

st.divider()

st.subheader("Perfil do Cliente")

distribution = query_df(
    """
    WITH base AS (
        SELECT
            f.sk_id_curr,
            f.target,
            f.amt_income_total,
            r.age_band,
            r.income_band,
            r.name_family_status,
            r.name_income_type,
            r.name_education_type,
            CASE WHEN r.code_gender = 'M' THEN 'Masculino' WHEN r.code_gender = 'F' THEN 'Feminino' ELSE NULL END AS code_gender,
        FROM gold.fact_credit_risk f
        LEFT JOIN gold.dim_requester r
            ON f.requester_key = r.requester_key
    )
    SELECT
        'Faixa de renda' AS distribution_type,
        COALESCE(income_band, 'Unknown') AS bucket,
        COUNT(DISTINCT sk_id_curr) AS clients,
        AVG(CAST(target AS INTEGER)) AS default_rate,
        AVG(amt_income_total) AS avg_income
    FROM base
    GROUP BY 1, 2
    UNION ALL
    SELECT
        'Faixa etária' AS distribution_type,
        COALESCE(age_band, 'Unknown') AS bucket,
        COUNT(DISTINCT sk_id_curr) AS clients,
        AVG(CAST(target AS INTEGER)) AS default_rate,
        AVG(amt_income_total) AS avg_income
    FROM base
    GROUP BY 1, 2
    UNION ALL 
    SELECT
        'Tipo de Família' AS distribution_type,
        COALESCE(name_family_status, 'Unknown') AS bucket,
        COUNT(DISTINCT sk_id_curr) AS clients,
        AVG(CAST(target AS INTEGER)) AS default_rate,
        AVG(amt_income_total) AS avg_income
    FROM base
    GROUP BY 1, 2
    UNION ALL 
    SELECT
        'Tipo de Trabalho' AS distribution_type,
        COALESCE(name_income_type, 'Unknown') AS bucket,
        COUNT(DISTINCT sk_id_curr) AS clients,
        AVG(CAST(target AS INTEGER)) AS default_rate,
        AVG(amt_income_total) AS avg_income
    FROM base
    GROUP BY 1, 2
    UNION ALL 
    SELECT
        'Educação' AS distribution_type,
        COALESCE(name_education_type, 'Unknown') AS bucket,
        COUNT(DISTINCT sk_id_curr) AS clients,
        AVG(CAST(target AS INTEGER)) AS default_rate,
        AVG(amt_income_total) AS avg_income
    FROM base
    GROUP BY 1, 2
    UNION ALL 
    SELECT
        'Gênero' AS distribution_type,
        COALESCE(code_gender, 'Unknown') AS bucket,
        COUNT(DISTINCT sk_id_curr) AS clients,
        AVG(CAST(target AS INTEGER)) AS default_rate,
        AVG(amt_income_total) AS avg_income
    FROM base
    GROUP BY 1, 2
    ORDER BY distribution_type, bucket
    """,
    warehouse_path,
)

left, right = st.columns(2)

with (left):
    income_distribution = distribution[distribution["distribution_type"] == "Faixa de renda"
    ].set_index("bucket", drop=False).reindex(index=income_order)
    fig = px.bar(
        income_distribution,
        x="bucket",
        y="clients",
        color="default_rate",
        text="clients",
        labels={"bucket": "Faixa de renda", "clients": "Clientes", "default_rate": "Inadimplência"},
        title="Distribuição de renda",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with (right):
    age_distribution = distribution[distribution["distribution_type"] == "Faixa etária"
    ].set_index("bucket", drop=False).reindex(index=age_order)
    fig = px.bar(
        age_distribution,
        x="bucket",
        y="clients",
        color="default_rate",
        text="clients",
        labels={"bucket": "Faixa etária", "clients": "Clientes", "default_rate": "Inadimplência"},
        title="Distribuição de idade"
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with (left):
    gender_distribution = distribution[distribution["distribution_type"] == "Gênero"
    ]
    fig = px.bar(
        gender_distribution,
        x="bucket",
        y="clients",
        color="default_rate",
        text="clients",
        labels={"bucket": "Tipo de Família", "clients": "Clientes", "default_rate": "Inadimplência"},
        title="Distribuição de Gênero",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with (right):
    family_distribution = distribution[distribution["distribution_type"] == "Tipo de Família"
    ]
    fig = px.bar(
        family_distribution,
        x="bucket",
        y="clients",
        color="default_rate",
        text="clients",
        labels={"bucket": "Faixa etária", "clients": "Clientes", "default_rate": "Inadimplência"},
        title="Distribuição de Estado Civil",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with (left):
    education_distribution = distribution[distribution["distribution_type"] == "Educação"
    ]
    fig = px.bar(
        education_distribution,
        x="bucket",
        y="clients",
        color="default_rate",
        text="clients",
        labels={"bucket": "Tipo de Família", "clients": "Clientes", "default_rate": "Inadimplência"},
        title="Distribuição de Educação",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

with (right):
    work_distribution = distribution[distribution["distribution_type"] == "Tipo de Trabalho"
    ]
    fig = px.bar(
        work_distribution,
        x="bucket",
        y="clients",
        color="default_rate",
        text="clients",
        labels={"bucket": "Faixa etária", "clients": "Clientes", "default_rate": "Inadimplência"},
        title="Distribuição de Tipo de Trabalho"
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

min_clients = st.sidebar.number_input("Mínimo de clientes por grupo", min_value=1, value=100, step=100)

combined_profile = query_df(
    """
    WITH portfolio AS (
        SELECT AVG(CAST(target AS INTEGER)) AS baseline_default_rate
        FROM gold.fact_credit_risk
    )
    SELECT
        CASE
            WHEN requester.code_gender = 'F' THEN 'Feminino'
            WHEN requester.code_gender = 'M' THEN 'Masculino'
            ELSE requester.code_gender
        END AS genero,
        requester.age_band AS faixa_idade,
        requester.income_band AS faixa_renda,
        COUNT(DISTINCT fact.sk_id_curr) AS clientes,
        AVG(CAST(fact.target AS INTEGER)) AS taxa_inadimplencia,
        AVG(CAST(fact.target AS INTEGER))
            / NULLIF(MAX(portfolio.baseline_default_rate), 0) AS lift_risco,
        AVG(CAST(fact.target AS INTEGER))
            - MAX(portfolio.baseline_default_rate) AS lift_pp
    FROM gold.fact_credit_risk AS fact
    CROSS JOIN portfolio
    LEFT JOIN gold.dim_requester AS requester
        ON fact.requester_key = requester.requester_key
    WHERE requester.code_gender IS NOT NULL
      AND requester.code_gender <> 'XNA'
      AND requester.age_band NOT IN ('Unknown', 'Outlier')
      AND requester.income_band NOT IN ('Unknown', 'Outlier')
    GROUP BY 1, 2, 3
    HAVING COUNT(DISTINCT fact.sk_id_curr) >= ?
    ORDER BY lift_risco DESC NULLS LAST, clientes DESC
    """,
    warehouse_path,
    [min_clients],
)

st.subheader("Inadimplência por segmento")


st.markdown(
    """
    Essa seção tem o objetivo de mostrar a inadimplências dos grupos por gênero, idade e faixa salarial.
    A cor representa lift de inadimplência contra a média da carteira:
    - Verde indica risco abaixo da média 
    - Amarelo próximo da média 
    - Vermelho acima da média 
    
    O hover mostra volume, inadimplência e diferença em pontos percentuais.
    """
)


selected_profile = combined_profile.copy()

selected_profile = selected_profile.copy()
selected_profile["lift_label"] = selected_profile["lift_risco"].map(lambda value: f"{value:.1f}x")
selected_profile["risk_bucket"] = selected_profile["lift_risco"].map(
    lambda value: "Alto risco"
    if value >= 1.25
    else "Baixo risco"
    if value <= 0.85
    else "Próximo da média"
)


fig = px.scatter(
    selected_profile,
    x="faixa_renda",
    y="faixa_idade",
    color="lift_risco",
    text="lift_label",
    facet_col="genero",
    category_orders={
        "faixa_renda": income_order,
        "faixa_idade": age_order,
        "genero": ["Feminino", "Masculino"],
    },
    color_continuous_scale="RdYlGn_r",
    range_color=[0.65, 1.75],
    custom_data=[
        "genero",
        "clientes",
        "taxa_inadimplencia",
        "lift_risco",
        "lift_pp",
        "risk_bucket",
    ],
    labels={
        "faixa_renda": "Faixa salarial",
        "faixa_idade": "Faixa etária",
        "lift_risco": "Lift vs carteira",
    },
)
fig.update_traces(
    marker_symbol="square",
    marker_size=46,
    marker_line_width=1,
    marker_line_color="white",
    textposition="middle center",
    textfont={"size": 11, "color": "#111"},
    hovertemplate=(
        "<b>%{customdata[5]}</b><br>"
        "Gênero: %{customdata[0]}<br>"
        "Faixa salarial: %{x}<br>"
        "Faixa etária: %{y}<br>"
        "Clientes: %{customdata[1]:,.0f}<br>"
        "Inadimplência: %{customdata[2]:.2%}<br>"
        "Lift: %{customdata[3]:.2f}x<br>"
        "Diferença vs média: %{customdata[4]:+.2%}<extra></extra>"
    ),
)
fig.update_layout(
    xaxis_tickangle=-30,
    coloraxis_colorbar_title="Lift",
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

