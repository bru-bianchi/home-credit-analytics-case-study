# Regras de Negócio

Este documento resume os principais sinais de risco criados nas camadas `silver` e `gold`. Ele não é um dicionário
exaustivo de colunas; o objetivo é explicar quais decisões analíticas sustentam as features e por que elas importam para
o negócio.

## Convenções

- `flag_*`: indicador booleano de comportamento, ausência de informação ou categoria relevante.
- `*_ratio` e `*_rate`: proporções usadas para comparar clientes em diferentes escalas.
- `*_count`, `total_*`, `avg_*` e `wavg_*`: agregações históricas usadas para resumir comportamento ao longo do tempo.
- Thresholds de negócio ficam explícitos no SQL para facilitar auditoria.

## Sinais Principais

| Tema | Importância para o negócio | Exemplos de variáveis | Implementação |
|---|---|---|---|
| Atraso e inadimplência histórica | Identifica clientes com comportamento anterior de atraso, um dos sinais mais fortes para risco de crédito | `flag_has_dpd`, `flag_severe_dpd`, `flag_recent_dpd`, `dpd_ratio`, `severe_dpd_ratio`, `pos_dpd_ratio` | [bureau_balance](../sql/silver/020_bureau_balance.sql), [bureau](../sql/silver/030_bureau.sql), [POS Cash](../sql/silver/070_POS_Cash_balance.sql), [agregações externas](../sql/silver/080_bureau_info_agg.sql), [agregações internas](../sql/silver/090_previous_application_agg.sql) |
| Crédito recente e exposição externa | Mostra recência e volume de relacionamento de crédito fora da instituição | `flag_recent_credit`, `external_recent_credit`, `bureau_recent_credit_count`, `bureau_total_credit`, `bureau_total_overdue_amount` | [bureau](../sql/silver/030_bureau.sql), [dim_risk_segment](../sql/gold/040_BI_dim_risk_segment.sql), [fact_credit_risk](../sql/gold/060_BI_fact_table.sql) |
| Capacidade financeira | Compara valor do crédito, renda e anuidade para medir comprometimento financeiro | `loan_income_ratio`, `annuity_income_ratio`, `annuity_credit_ratio`, `debt_good_ratio`, `income_per_person` | [applications](../sql/silver/010_applications.sql), [fact_credit_risk](../sql/gold/060_BI_fact_table.sql) |
| Histórico interno | Resume relacionamento anterior com a instituição: aprovações, recusas, uso de produtos e comportamento de pagamento | `prev_applications_total`, `prev_applications_refused`, `prev_approved_credit_ratio`, `prev_unpaid_amount_for_installments`, `avg_payment_ratio` | [previous_application](../sql/silver/040_previous_application.sql), [installments](../sql/silver/050_installments_payments.sql), [agregações internas](../sql/silver/090_previous_application_agg.sql), [fact_credit_risk](../sql/gold/060_BI_fact_table.sql) |
| Cartão e utilização de limite | Captura uso intensivo ou acima do limite, que pode indicar pressão de liquidez | `flag_high_utilization`, `flag_over_utilization`, `credit_utilization_ratio`, `max_credit_utilization`, `avg_credit_utilization` | [credit_card_balance](../sql/silver/060_credit_card_balance.sql), [agregações internas](../sql/silver/090_previous_application_agg.sql), [dim_risk_segment](../sql/gold/040_BI_dim_risk_segment.sql) |
| Pagamento de parcelas | Mede atraso, pagamento parcial e valor em aberto em contratos anteriores | `flag_late_payment`, `flag_partial_payment`, `days_late`, `payment_ratio`, `unpaid_amount` | [installments_payments](../sql/silver/050_installments_payments.sql), [agregações internas](../sql/silver/090_previous_application_agg.sql) |
| Perfil e estabilidade cadastral | Ajuda a segmentar risco por renda, idade, ocupação, moradia e estabilidade de emprego | `age_years`, `employment_years`, `flag_employed`, `flag_self_employed`, `flag_economically_inactive`, `flag_married` | [applications](../sql/silver/010_applications.sql), [dim_requester](../sql/gold/020_BI_dim_requester.sql) |
| Completude de informação | Diferencia ausência real de informação de valor observado e ajuda a avaliar qualidade do cadastro | `housing_info_fill_rate`, `contact_info_filled_rate`, `ext_source_fill_rate`, `document_provided_rate`, `cadastral_completeness_rate` | [applications](../sql/silver/010_applications.sql), [fact_credit_risk](../sql/gold/060_BI_fact_table.sql) |
| Segmentação executiva | Transforma variáveis contínuas em faixas compreensíveis para análise de negócio e dashboard | `age_band`, `income_band`, `employment_tenure_band`, `mean_score_band`, `annuity_income_band` | [ref_band_rules](../sql/gold/005_ref_band_rules.sql), [dim_requester](../sql/gold/020_BI_dim_requester.sql), [dim_risk_segment](../sql/gold/040_BI_dim_risk_segment.sql) |
| Modelagem preditiva | Consolida sinais numéricos e booleanos em uma matriz única para previsão de inadimplência | `target`, `flag_test`, one-hot encodings, ratios financeiros, taxas históricas e flags de ausência de histórico | [feature store de ML](../sql/gold/010_ML_feature_store.sql) |

## Regras De Threshold

| Regra | Definição atual |
|---|---|
| DPD externo | Status mensal em `('1', '2', '3', '4', '5')` ou valor vencido maior que zero |
| DPD severo externo | Status mensal em `('3', '4', '5')` |
| DPD POS Cash | `sk_dpd > 0` |
| DPD severo POS Cash | `sk_dpd > 60` |
| Crédito recente | `ABS(days_credit) <= 30` |
| Aplicação recente | `ABS(days_decision) <= 30` |
| Longo prazo | `cnt_payment >= 24` |
| Próximo da quitação | `cnt_instalment_future <= 3` |
| Alta utilização de cartão | `amt_balance / amt_credit_limit_actual >= 0.8` |
| Uso acima do limite | `amt_balance / amt_credit_limit_actual > 1` |
| Alto volume de saques | `cnt_drawings_current >= 5` |

## Regras De Faixas

As faixas usadas na Gold ficam versionadas em [docs/references/gold_band_rules.csv](./references/gold_band_rules.csv).
Elas são carregadas em `gold.ref_band_rules` e aplicadas nas dimensões para facilitar leitura executiva, comparação entre
segmentos e filtros no dashboard.

## Curadoria Para Modelagem

A tabela `gold.credit_risk_feature_store` aplica uma curadoria adicional sobre os sinais disponíveis: remove campos muito
esparsos, evita pares redundantes de contagem e média quando uma taxa é mais estável, e transforma categorias relevantes
em one-hot encoding. Essa decisão mantém a base pronta para modelos tabulares sem deslocar regras essenciais para fora do
SQL.
