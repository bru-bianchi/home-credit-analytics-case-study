# Ingestão Silver

A camada `silver` transforma a Bronze em uma base analítica enriquecida. Ela concentra regras de negócio, features e
agregações históricas que servem tanto para exploração técnica quanto para construção da camada Gold.

## Resumo Executivo

| Decisão | Implementação | Benefício |
|---|---|---|
| Usar SQL versionado | Transformações em `sql/silver/` | Reprodutibilidade e revisão clara das regras analíticas |
| Materializar a camada | Parquet em `data/silver/` e schema `silver` no DuckDB | Consumo mais rápido e desacoplado da Bronze |
| Separar detalhe e histórico | Tabelas detalhadas + agregações comportamentais | Permite análises em diferentes granularidades |
| Manter regras explícitas | `CASE`, `COALESCE`, `NULLIF`, flags e ratios no próprio SQL | Evita regras escondidas e facilita auditoria |
| Reaproveitar resultados válidos | Cache por fingerprint de SQL, dependências e schema | Reduz reprocessamento desnecessário |

## Objetivo

Consolidar dados confiáveis e enriquecidos para consumo analítico detalhado e histórico.

Na prática, a Silver responde a três necessidades:

- transformar bases técnicas da Bronze em tabelas interpretáveis para análise;
- criar sinais de risco reutilizáveis, como flags, ratios, scores derivados e métricas de completude;
- resumir históricos externos e internos em agregações úteis para segmentação, dashboard e modelagem.

## Desenho Da Camada

| Grupo | Tabelas | Papel |
|---|---|---|
| Aplicação atual | `applications` | Perfil, renda, contrato atual, scores externos, completude e base train/test |
| Histórico externo | `bureau`, `bureau_balance`, `agg_bureau_external_credit_behavior` | Crédito em outras instituições, DPD, bad debt, valores vencidos e recência |
| Histórico interno | `previous_application`, `installments_payments`, `credit_card_balance`, `pos_cash_balance`, `agg_internal_historical_behavior` | Aplicações anteriores, pagamentos, cartão, POS Cash e comportamento de uso de crédito |

## Features Criadas

A Silver cria features novas em quatro grupos principais:

- **Perfil e cadastro:** idade, tempo de emprego, ocupação tratada, estado civil, posse de carro/imóvel e flags de
  ausência de informação.
- **Capacidade financeira:** `loan_income_ratio`, `annuity_income_ratio`, `annuity_credit_ratio`,
  `debt_good_ratio` e `income_per_person`.
- **Comportamento de crédito:** DPD, DPD severo, crédito recente, bad debt, utilização de cartão, pagamento mínimo,
  saque, atraso em parcelas e pagamento parcial.
- **Completude de dados:** taxas de preenchimento para moradia, contato, perfil cadastral, scores externos, bureau,
  círculo social e documentos.

## Agregações Históricas

As agregações reduzem históricos mensais ou contratuais para sinais consumíveis por cliente ou contrato anterior.

| Tabela | Origem | Principais sinais |
|---|---|---|
| `agg_bureau_external_credit_behavior` | `bureau` + `bureau_balance` | DPD externo, DPD severo, meses em atraso, bad debt, dívida, atraso e ausência de histórico mensal |
| `agg_internal_historical_behavior` | `previous_application`, `installments_payments`, `credit_card_balance`, `pos_cash_balance` | aprovações/recusas anteriores, atraso em parcelas, utilização de cartão, pagamento parcial, POS Cash e valores em aberto |

Essas agregações são a principal ponte entre eventos históricos de alta granularidade e a camada Gold, que precisa de
sinais consolidados para análise executiva.

## Tabelas Publicadas

| Tabela | Descrição |
|---|---|
| `silver.applications` | Consolidação de `application_train` e `application_test`, com flags cadastrais, ratios financeiros, scores externos e completude |
| `silver.bureau_balance` | Status mensal de créditos externos, com flags de DPD, DPD severo, DPD recente, crédito fechado e status ausente |
| `silver.bureau` | Histórico externo no nível de crédito, com crédito ativo, bad debt, crédito recente, tipo de crédito e ratios de dívida/atraso |
| `silver.previous_application` | Aplicações anteriores, com status, tipo de contrato, recorrência, prazo, diferenças de valor e ratios de aprovação |
| `silver.installments_payments` | Pagamentos parcelados, com atraso, pagamento antecipado, pagamento parcial, dias de atraso e razão de pagamento |
| `silver.credit_card_balance` | Histórico de cartão, com utilização de limite, uso acima do limite, pagamento mínimo e saque |
| `silver.pos_cash_balance` | Histórico POS Cash, com DPD, DPD severo, contrato ativo e razão de parcelas restantes |
| `silver.agg_bureau_external_credit_behavior` | Agregação de comportamento externo para risco |
| `silver.agg_internal_historical_behavior` | Agregação de comportamento interno em contratos anteriores |

## Execução, Metadados E Cache

Script de execução:

- [scripts/2_run_silver_transformation.py](../scripts/2_run_silver_transformation.py)

O runner descobre os SQLs em `sql/silver/`, resolve dependências entre `bronze.*` e `silver.*`, exporta Parquet para
`data/silver/` e registra eventos em `metadados.pipeline_events`.

O cache evita reprocessamento quando SQL, dependências e schema permanecem iguais. O relatório consolidado fica em
`artifacts/silver/silver_transformation_report.json`.

## Relação Com A Gold

A Gold consome principalmente:

- `silver.applications`, como base da aplicação atual e do cliente;
- `silver.agg_bureau_external_credit_behavior`, como resumo do histórico externo;
- `silver.agg_internal_historical_behavior`, como resumo do histórico interno.

Essas três tabelas também sustentam a feature store de ML na Gold. Com isso, a Silver preserva granularidade e riqueza
analítica, enquanto a Gold entrega tanto uma visão simples para negócio quanto uma matriz curada para previsão de
inadimplência.
