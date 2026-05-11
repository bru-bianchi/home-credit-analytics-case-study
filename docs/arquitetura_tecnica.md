# Arquitetura Técnica

Este documento resume as escolhas técnicas efetivamente adotadas para executar o pipeline completo localmente no estado
atual do projeto.

## Visão geral

A stack atual foi desenhada para:

- executar o pipeline localmente de ponta a ponta;
- manter reprodutibilidade a partir dos arquivos originais em `data/raw/`;
- publicar camadas analíticas em `parquet`;
- usar o DuckDB como warehouse local, engine analítica e store de metadados;
- reduzir reprocessamento com cache incremental baseado em fingerprints e metadados.

## Componentes principais

### Linguagem e orquestração

- `Python` como linguagem principal de orquestração do pipeline;
- scripts CLI por camada em `scripts/`:
  - `scripts/0_run_raw_ingestion_audit.py`
  - `scripts/1_run_bronze_transformation.py`
  - `scripts/2_run_silver_transformation.py`
- organização do código em `src/credit_risk_pipeline/` e `src/utils/`.

Papel atual do Python:

- coordenar a execução por camada;
- ler e validar os arquivos raw;
- planejar e publicar a `bronze`;
- descobrir SQLs, resolver dependências e executar a `silver`;
- persistir metadados e relatórios de execução.

### Engine analítica e warehouse

- `DuckDB 1.4.4` como engine analítica local;
- warehouse local em `data/warehouse/credit_risk.duckdb`;
- uso do DuckDB para:
  - leitura e escrita das tabelas das camadas;
  - execução dos SQLs versionados da `silver`;
  - persistência de metadados e auditoria;
  - exploração local via DuckDB CLI ou UI.

Schemas atualmente usados no warehouse:

- `bronze`
- `silver`
- `metadados`

### Formato de dados

- `CSV` como formato de entrada em `data/raw/`;
- `Parquet` com `snappy` como formato físico das camadas processadas:
  - `data/bronze/`
  - `data/silver/`
  - `data/gold/` como destino previsto

Motivos práticos para `parquet` nas camadas analíticas:

- preservação mais estável de schema;
- melhor performance de leitura analítica;
- compressão mais eficiente;
- menor atrito de parsing em comparação com CSV.

### Transformações por camada

- `raw`: validação estrutural e registro de metadados;
- `bronze`: transformação técnica em `Python`, com schema mapping versionado, casts explícitos e publicação em
  `parquet`;
- `silver`: transformação analítica orientada por `SQL` versionado em `sql/silver/`, com tabelas base e agregadas
  `_agg`;
- `gold`: camada prevista para marts, agregações prontas e tabela final de modelagem para ML.

### Metadados e observabilidade

- metadados persistidos no próprio DuckDB;
- tabelas atuais de observabilidade:
  - `metadados.raw_validation_events`
  - `metadados.pipeline_events`
- relatórios de execução gravados em `artifacts/` por camada.

Objetivos desses metadados:

- auditoria das execuções;
- rastreabilidade por arquivo, tabela e run;
- suporte a cache incremental;
- diagnóstico de falhas e divergências de schema.

## Estratégia de cache incremental

O pipeline atual já implementa reaproveitamento incremental nas camadas executadas até aqui.

### Raw

- cache por `file_fingerprint` e `process_version`;
- o fingerprint considera caminho, tamanho em bytes e timestamp de modificação do arquivo;
- quando o arquivo permanece inalterado, a validação estrutural é reaproveitada.

### Bronze

- cache condicionado por:
  - fingerprint do arquivo raw de origem;
  - versão da transformação;
  - schema planejado;
  - existência do parquet e da tabela no warehouse.

### Silver

- cache condicionado por:
  - fingerprint do SQL da tabela;
  - fingerprints das dependências em `bronze.*` e `silver.*`;
  - schema atual da tabela;
  - existência do parquet e da tabela no warehouse.

## Organização dos artefatos

- `data/raw/`: origem intocada;
- `data/bronze/`: parquets da camada bronze;
- `data/silver/`: parquets da camada silver;
- `data/warehouse/`: DuckDB local;
- `artifacts/ingestion/`: relatórios da validação raw;
- `artifacts/bronze/`: planos e relatórios da bronze;
- `artifacts/silver/`: relatórios da silver;
- `sql/silver/`: SQLs versionados da camada silver.

## Dependências atuais

Dependência explicitamente versionada no projeto neste momento:

- `duckdb==1.4.4`

Observação:

- o projeto usa o ambiente virtual `.venv` para execução local;
- o foco até aqui foi consolidar o pipeline e o warehouse local antes de expandir a lista de dependências.

## Nota de arquitetura

- O `DuckDB` foi escolhido neste projeto como engine analítica local e de desenvolvimento.
- A arquitetura atual é intencionalmente local, batch e orientada a arquivos estáticos.
- Para uma solução mais robusta e contínua, com bases atualizadas recorrentemente, a arquitetura alvo será reavaliada
  na etapa de proposta em AWS, incluindo práticas de produção e infraestrutura como código.
- Como proposta de produção, a arquitetura alvo deverá evoluir para um modelo baseado em `data lake` ou `lakehouse`,
  garantindo maior estruturação dos dados, histórico, escalabilidade e melhor suporte a cargas recorrentes.
