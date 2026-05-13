# Decisões de Modelagem

Este projeto separa claramente a camada física dos dados, a camada lógica de consulta e as camadas de negócio. A decisão
principal foi manter os arquivos originais auditáveis, materializar as camadas analíticas em Parquet e usar o DuckDB como
warehouse local para exploração, joins, queries e consumo pelo dashboard.

## Resumo Executivo

| Decisão | Implementação | Benefício                                                                                   |
|---|---|---------------------------------------------------------------------------------------------|
| Preservar a origem | CSVs originais em `data/raw/` | Auditoria, reprodutibilidade e reprocessamento                                              |
| Materializar camadas analíticas | Parquet em `data/bronze/`, `data/silver/` e `data/gold/` | Melhor performance, compressão e estabilidade de schema                                     |
| Separar camada física e lógica | DuckDB em `data/warehouse/credit_risk.duckdb` | Queries, joins, metadados e consumo analítico sem depender diretamente dos CSVs ou Parquets |
| Organizar consumo por maturidade | Camadas `raw`, `bronze`, `silver` e `gold` | Clareza entre dado original, dado técnico, dado enriquecido e dado de negócio               |
| Publicar a Gold para consumo | Star schema + feature store de ML | Dashboard, análises executivas e modelagem preditiva com menor complexidade para o consumidor |

## Desenho Das Camadas

| Camada | Papel | Saída principal | Consumidor esperado |
|---|---|---|---|
| `raw` | Preservar os arquivos como recebidos | CSV original | Pipeline e auditoria |
| `bronze` | Padronizar tecnicamente os dados | Parquet técnico e schema `bronze` | Engenharia e próximas etapas do pipeline |
| `silver` | Aplicar regras, features e agregações históricas | Parquet enriquecido e schema `silver` | Análises detalhadas e construção da Gold |
| `gold` | Servir dados prontos para consumo | Star schema, fato, dimensões, feature store e Parquet final | Dashboard, negócio e modelagem preditiva |
| `metadados` | Registrar execuções e rastreabilidade | Tabelas de eventos no DuckDB | Auditoria técnica e diagnóstico |

## Racional Técnico

Manter CSV em `raw` evita perda de rastreabilidade: qualquer decisão de tratamento pode ser reprocessada a partir da
fonte original, sem alterar o dado recebido.

Persistir `bronze`, `silver` e `gold` em Parquet reduz custo de leitura, melhora compressão, preserva tipos de forma mais
estável e evita problemas recorrentes de parsing e inferência de CSV.

Usar DuckDB como warehouse local centraliza a camada lógica do projeto: as tabelas ficam organizadas em schemas, os SQLs
podem fazer joins e agregações de forma simples, e os metadados de execução ficam próximos das tabelas processadas.

A Gold foi separada em dois formatos de consumo porque eles resolvem problemas diferentes: o star schema facilita leitura
executiva, filtros e métricas de dashboard, enquanto `gold.credit_risk_feature_store` entrega uma matriz tabular curada
para prever inadimplência, sem depender de joins adicionais na etapa de modelagem.

## Links De Detalhamento

- [Fontes de dados](./fontes_de_dados.md)
- [Ingestão raw](./ingestao_raw.md)
- [Ingestão bronze](./ingestao_bronze.md)
- [Ingestão silver](./ingestao_silver.md)
- [Ingestão gold](./ingestao_gold.md)
