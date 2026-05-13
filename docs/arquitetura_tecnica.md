# Arquitetura Técnica

Este documento resume a arquitetura de execução local do projeto. A modelagem das camadas, regras de negócio e detalhes
de cada transformação ficam nos documentos específicos referenciados ao final.

## Visão Executiva

| Componente | Escolha | Papel |
|---|---|---|
| Linguagem | Python | Orquestração local das etapas do pipeline |
| Engine analítica | DuckDB | Execução SQL, warehouse local e persistência de metadados |
| Entrada e armazenamento | CSV raw + Parquet processado | Camada física descrita em [Decisões de modelagem](./decisoes_de_modelagem.md) |
| SQL versionado | `sql/silver/` e `sql/gold/` | Transformações auditáveis e reprodutíveis |
| Observabilidade | `artifacts/` + schema `metadados` | Relatórios, eventos de execução, fingerprints e diagnóstico |
| Dashboard | Streamlit sobre Gold/DuckDB/MotherDuck | Consumo executivo dos dados finais |

## Fluxo De Execução

O pipeline é executado localmente por scripts sequenciais:

```text
data/raw/*.csv
  -> scripts/0_run_raw_ingestion_audit.py
  -> scripts/1_run_bronze_transformation.py
  -> scripts/2_run_silver_transformation.py
  -> scripts/3_run_gold_transformation.py
  -> app/Home.py e app/pages/
```

O papel de cada camada está detalhado nas documentações de ingestão. Aqui, o ponto arquitetural é que cada etapa tem um
entrypoint explícito, grava artefatos próprios e registra metadados no DuckDB.

## Runtime Local

O projeto usa `Python` para coordenar as etapas e `DuckDB` como engine analítica local.

O DuckDB concentra:

- schemas `bronze`, `silver`, `gold` e `metadados`;
- execução das transformações SQL;
- leitura e escrita das tabelas materializadas;
- suporte a exploração local via CLI/UI;
- persistência de eventos de execução e cache incremental.

O arquivo principal do warehouse local é:

- `data/warehouse/credit_risk.duckdb`

## Metadados E Cache

O pipeline registra metadados no schema `metadados` do DuckDB.

Tabelas principais:

- `metadados.raw_validation_events`: eventos da validação dos arquivos raw.
- `metadados.pipeline_events`: eventos das camadas transformadas.

Esses registros sustentam auditoria, diagnóstico de falhas e cache incremental. Os critérios específicos de
reprocessamento são descritos nas docs de cada camada.

## Dependências

A dependência central do pipeline é:

- `duckdb==1.4.4`

As demais dependências ficam versionadas em:

- `requirements.txt`

## Documentos Relacionados

- [Decisões de modelagem](./decisoes_de_modelagem.md)
- [Ingestão raw](./ingestao_raw.md)
- [Ingestão bronze](./ingestao_bronze.md)
- [Ingestão silver](./ingestao_silver.md)
- [Ingestão gold](./ingestao_gold.md)
- [Regras de negócio](./regras_de_negocio.md)
