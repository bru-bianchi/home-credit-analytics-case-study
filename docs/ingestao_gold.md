# Ingestão Gold

A camada `gold` é a camada de consumo do projeto. Ela transforma os dados enriquecidos da Silver em tabelas prontas para
análise executiva, dashboard e modelagem preditiva de inadimplência.

## Resumo Executivo

| Decisão                         | Implementação                                           | Benefício                                             |
|---------------------------------|---------------------------------------------------------|-------------------------------------------------------|
| Organizar consumo por negócio   | Star schema com fato e dimensões                        | Simplifica queries recorrentes e dashboards           |
| Centralizar métricas executivas | `gold.fact_credit_risk`                                 | Uma visão consolidada por cliente/aplicação           |
| Separar atributos descritivos   | `dim_requester`, `dim_contract`, `dim_risk_segment`     | Facilita filtros, segmentações e quebras analíticas   |
| Publicar base de modelagem      | `gold.credit_risk_feature_store`                        | Dataset tabular curado para previsão de inadimplência |
| Versionar regras de faixas      | `gold.ref_band_rules` a partir de `gold_band_rules.csv` | Segmentações auditáveis e fáceis de revisar           |
| Materializar a camada           | Parquet em `data/gold/` e schema `gold` no DuckDB       | Consumo mais rápido por dashboard e análises finais   |

## Objetivo

Servir como camada final de análise para o time de negócio e como origem dos dashboards.

Na prática, a Gold responde a três necessidades:

- entregar tabelas mais simples para consumo executivo;
- consolidar métricas de inadimplência, exposição, histórico e comportamento de crédito;
- separar fatos e dimensões para facilitar filtros, segmentações e leitura pelo dashboard;
- disponibilizar uma feature store tabular para experimentação e treino de modelos de risco.

## Modelo Dimensional

O modelo principal segue uma estrutura em estrela:

| Tipo       | Tabela                  | Papel                                                                                    |
|------------|-------------------------|------------------------------------------------------------------------------------------|
| Fato       | `gold.fact_credit_risk` | Métricas centrais de risco, exposição e comportamento, uma linha por `sk_id_curr`        |
| Dimensão   | `gold.dim_requester`    | Perfil demográfico, socioeconômico, ocupacional, educação, bens e faixas do solicitante  |
| Dimensão   | `gold.dim_contract`     | Características do contrato atual e tipo de produto                                      |
| Dimensão   | `gold.dim_risk_segment` | Segmentos de risco baseados em sinais internos, externos, scores e ausência de histórico |
| Referência | `gold.ref_band_rules`   | Regras auditáveis de faixas usadas pelas dimensões                                       |

A feature store de ML é uma entrega complementar ao modelo dimensional. Ela não usa as dimensões Gold nem as regras de
faixa: sua função é disponibilizar uma matriz de features numérica/booleana, com uma linha por `sk_id_curr`, adequada
para treino e scoring.

## Tabelas Publicadas

| Tabela                           | Conteúdo                                                                                                                |
|----------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `gold.ref_band_rules`            | Regras versionadas de faixas carregadas de `docs/references/gold_band_rules.csv`                                        |
| `gold.dim_requester`             | Dados do solicitante, incluindo idade, renda, ocupação, educação, moradia, bens e faixas                                |
| `gold.dim_contract`              | Tipo de contrato atual e flags de produto                                                                               |
| `gold.dim_risk_segment`          | Sinais de risco internos/externos, score externo, faixas e flags de ausência de histórico                               |
| `gold.fact_credit_risk`          | Fato central com target, valores financeiros, ratios, histórico externo/interno e completude cadastral                  |
| `gold.credit_risk_feature_store` | Tabela analítica final para modelagem de inadimplência, com `target`, `flag_test`, one-hot encodings e features curadas |

## Métricas Principais

A tabela fato `gold.fact_credit_risk` consolida métricas desenhadas para análise executiva de inadimplência.

| Grupo                | Exemplos                                                                                                  |
|----------------------|-----------------------------------------------------------------------------------------------------------|
| Inadimplência        | `target`, taxa de inadimplência e lift contra baseline calculados no dashboard                            |
| Exposição financeira | valor de crédito, anuidade, preço do bem, renda e valores vencidos                                        |
| Ratios financeiros   | `loan_income_ratio`, `annuity_income_ratio`, `annuity_credit_ratio`, `debt_good_ratio`                    |
| Histórico externo    | quantidade de créditos no bureau, créditos ativos, bad debt, DPD, DPD severo e dívida em aberto           |
| Histórico interno    | aplicações anteriores, aprovações, recusas, utilização de cartão, pagamentos parciais, atrasos e POS Cash |
| Completude cadastral | preenchimento de moradia, contato, scores externos, círculo social e documentos                           |

## Feature Store De ML

A tabela `gold.credit_risk_feature_store` consolida as variáveis candidatas para modelos de previsão de inadimplência.
Ela parte de `silver.applications` e adiciona resumos históricos de crédito externo e interno já criados na Silver.

Decisões aplicadas:

- manter `target` como variável resposta para treino e `flag_test` para separar a base sem resposta;
- usar apenas `silver.applications`, `silver.agg_bureau_external_credit_behavior` e
  `silver.agg_internal_historical_behavior`;
- remover variáveis com missing rate extremo ou baixa utilidade direta para modelagem tabular;
- reduzir redundância entre contagens, somas e médias, priorizando taxas, médias, máximos e flags mais interpretáveis;
- converter campos categóricos importantes em one-hot encoding, como gênero, renda, educação, família, moradia e
  ocupações principais;
- manter flags de ausência de histórico, porque ausência de bureau ou histórico interno também é sinal relevante de
  risco.

Essa tabela é mais enxuta que uma extração exploratória ampla: ela preserva cobertura dos principais blocos de risco,
mas evita expor variáveis brutas ou altamente esparsas que exigiriam tratamento adicional fora do SQL.

A imputação de valores nulos não foi aplicada nesta tabela, pois a estratégia adequada pode variar conforme o modelo
estatístico ou algoritmo utilizado, devendo ser definida no pipeline de modelagem pelo time de Ciência de Dados.

## Dependências

A Gold consome principalmente:

- `silver.applications`, como base da aplicação atual e do solicitante;
- `silver.agg_bureau_external_credit_behavior`, como resumo do histórico externo;
- `silver.agg_internal_historical_behavior`, como resumo do histórico interno;
- `docs/references/gold_band_rules.csv`, como fonte das faixas auditáveis.

A feature store de ML depende somente das três tabelas Silver acima. As regras de faixas em `gold.ref_band_rules` são
usadas nas dimensões e no consumo executivo, não na matriz final de modelagem.

As dimensões usam `gold.ref_band_rules` para aplicar faixas como:

- idade;
- renda;
- tempo de emprego;
- score externo médio;
- comprometimento da renda por anuidade.

## Execução E Observabilidade

Script de execução:

- [scripts/3_run_gold_transformation.py](../scripts/3_run_gold_transformation.py)

O runner descobre os SQLs em `sql/gold/`, resolve dependências entre `silver.*` e `gold.*`, exporta Parquet para
`data/gold/` e registra eventos em `metadados.pipeline_events`.

O relatório consolidado fica em `artifacts/gold/gold_transformation_report.json`.

## Relação Com O Dashboard

O dashboard consome principalmente a Gold porque ela já traz:

- fato central com métricas prontas;
- dimensões com chaves de segmentação;
- faixas analíticas padronizadas;
- sinais de risco interno e externo consolidados.

Essa separação reduz a complexidade das queries de visualização e evita que regras de negócio fiquem espalhadas na
camada de apresentação.

## Relação Com Modelagem Preditiva

Para modelagem, a Gold oferece uma tabela única por cliente/aplicação, alinhada ao objetivo de prever inadimplência.
As variáveis combinam capacidade financeira, scores externos, completude cadastral, histórico externo de crédito e
comportamento interno em contratos anteriores. Essa estrutura evita que cada experimento precise reconstruir joins e
agregações históricas a partir das tabelas de detalhe.
