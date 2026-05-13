# Ingestão Bronze

A camada `bronze` transforma os CSVs originais da Raw em uma primeira versão técnica, padronizada e eficiente para
leitura analítica.

## Resumo Executivo

| Decisão | Implementação | Benefício |
|---|---|---|
| Converter CSV para Parquet | Saídas em `data/bronze/*.parquet` | Melhor performance, compressão e estabilidade de schema |
| Padronizar nomes | `snake_case` com referência oficial e overrides manuais | Nomes consistentes para SQL e consumo posterior |
| Controlar tipos explicitamente | `bronze_schema_mapping.csv` | Evita inferência instável de CSV |
| Registrar exceções sem hardcode | CSVs de mapping em `docs/references/` | Regras versionadas e auditáveis |
| Manter escopo técnico | Sem joins, features ou regras complexas | Bronze continua próxima da origem, mas pronta para análise |
| Reaproveitar resultados válidos | Cache por fingerprint da raw, versão e schema planejado | Reduz reprocessamento desnecessário |

## Objetivo

Criar uma camada técnica confiável a partir dos arquivos originais, preservando a granularidade das bases e aplicando
apenas ajustes estruturais.

Na prática, a Bronze responde a três necessidades:

- transformar CSV em Parquet;
- estabilizar nomes, tipos e nullability;
- disponibilizar tabelas técnicas no schema `bronze` do DuckDB para as próximas camadas.

## Transformações Aplicadas

A Bronze aplica:

- padronização de nomes de colunas;
- casts explícitos definidos em `bronze_schema_mapping.csv`;
- conversão automática de colunas booleanas quando o domínio é compatível;
- substituição de sentinelas conhecidas por `NULL`;
- publicação em Parquet;
- carga no schema `bronze`;
- validação de schema planejado contra mapping versionado.

Ela não aplica:

- regras de negócio complexas;
- joins entre tabelas;
- imputações analíticas;
- criação de features;
- enriquecimentos da Silver.

## Arquivos De Referência

| Arquivo | Papel |
|---|---|
| `docs/references/HomeCredit_columns_description.csv` | Dicionário oficial de colunas do dataset, usado como referência de schema |
| `docs/references/bronze_column_mapping.csv` | Overrides manuais de nomes e correções semânticas |
| `docs/references/bronze_schema_mapping.csv` | Tipos e nullability esperados na Bronze |
| `docs/references/bronze_sentinel_mapping.csv` | Sentinelas conhecidas que devem ser substituídas por `NULL` |

## Mapeamento De Colunas

A resolução do nome final segue esta precedência:

1. override manual em `bronze_column_mapping.csv`;
2. nome esperado no dicionário `HomeCredit_columns_description.csv`;
3. fallback técnico para `snake_case` do nome original.

Exemplos:

- `SK_ID_BUREAU` em `bureau.csv` e `bureau_balance.csv` é padronizada para `sk_bureau_id`;
- `AMT_RECIVABLE` em `credit_card_balance.csv` é corrigida para `amt_receivable`.

Colunas identificadoras como `SK_ID_*` e `sk_bureau_id` são tratadas como `NOT NULL` quando definido pelo mapping da
Bronze.

## Execução E Observabilidade

Script de execução:

- [scripts/1_run_bronze_transformation.py](../scripts/1_run_bronze_transformation.py)

Saídas:

- Parquets em `data/bronze/`;
- tabelas no schema `bronze` do DuckDB;
- `artifacts/bronze/bronze_transformation_plan.json`, quando executado em dry-run;
- `artifacts/bronze/bronze_transformation_report.json`;
- eventos em `metadados.pipeline_events`.

## Cache E Reprocessamento

Uma tabela da Bronze só é reprocessada quando algum insumo técnico muda.

Critérios de reaproveitamento:

- Parquet já existe em `data/bronze/`;
- tabela já existe no schema `bronze`;
- fingerprint do arquivo raw permanece igual;
- versão da transformação Bronze permanece igual;
- schema planejado permanece igual.

Quando todos os critérios são atendidos, a tabela recebe status `skipped_cached_transformation`.

## Relação Com A Silver

A Bronze entrega uma base técnica confiável para a Silver.

Ela mantém os dados próximos da origem, mas com:

- nomes consistentes;
- tipos controlados;
- sentinelas tratadas;
- formato físico mais eficiente.

Com isso, a Silver pode se concentrar em regras analíticas, features e agregações históricas.
