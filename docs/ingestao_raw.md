# Ingestão de Dados Raw

Este documento descreve a etapa inicial de checagem, processamento técnico e carga local dos arquivos originais em
`data/raw/`.

## Objetivo

Garantir que os arquivos de origem estejam disponíveis, possam ser lidos corretamente e sejam preparados para o início
do pipeline analítico, sem aplicar ainda regras de negócio ou transformações analíticas das demais camadas.

## Escopo atual

Inclui:

- verificar se os arquivos esperados existem em `data/raw/`;
- validar se os CSVs podem ser lidos em Python;
- identificar estrutura básica de cada arquivo;
- registrar metadados da leitura;
- carregar os arquivos válidos para uma área técnica no DuckDB.

Não inclui:

- tratamento analítico de dados ausentes;
- correções de negócio;
- criação de features finais;
- joins analíticos entre tabelas;
- publicação das camadas `silver` e `gold`.

## Arquivos esperados

O processo atualmente espera os seguintes arquivos em `data/raw/`:

- `application_train.csv`
- `application_test.csv`
- `bureau.csv`
- `bureau_balance.csv`
- `previous_application.csv`
- `POS_CASH_balance.csv`
- `credit_card_balance.csv`
- `installments_payments.csv`

## Etapa 1: auditoria estrutural

O primeiro passo é uma auditoria simples dos arquivos raw.

Essa auditoria verifica:

- se o arquivo existe;
- se o arquivo está vazio;
- se a leitura do CSV funciona;
- quantidade de linhas;
- quantidade de colunas;
- nomes das colunas;
- tipos inferidos de forma básica;
- erros estruturais simples, como linhas com número inconsistente de colunas.

Além disso, a auditoria compara as colunas encontradas com a referência versionada do projeto:

- [HomeCredit_columns_description.csv](/Users/brunabianchi/Documents/home-credit-analytics-case-study/docs/references/HomeCredit_columns_description.csv)

Essa checagem classifica o schema de cada arquivo como:

- `ok`: estrutura esperada;
- `warning`: colunas esperadas ausentes ou colunas extras, sem quebra crítica;
- `error`: ausência de colunas obrigatórias, impedindo a continuidade da carga técnica.

Saída gerada:

- `artifacts/ingestion/raw_ingestion_report.json`

Script:

- [0_run_raw_ingestion_audit.py](/Users/brunabianchi/Documents/home-credit-analytics-case-study/scripts/0_run_raw_ingestion_audit.py)

## Etapa 2: carga técnica local no DuckDB

Depois da checagem, os arquivos legíveis são carregados no banco local para suporte à exploração inicial e à evolução do
pipeline.

Hoje essa carga ainda acontece em uma schema técnica `raw`, com o objetivo de:

- registrar os dados lidos localmente;
- permitir inspeção inicial dos datasets;
- manter rastreabilidade entre o CSV de origem e o conteúdo carregado;
- evitar recarga acidental do mesmo arquivo em reexecuções.

Antes de carregar um arquivo, o processo consulta o histórico de ingestões e verifica se aquele mesmo arquivo já foi
processado com sucesso anteriormente. Nesta versão, a checagem usa o caminho do arquivo e seu tamanho em bytes.

Saídas geradas:

- banco local em `data/warehouse/credit_risk.duckdb`;
- relatório em `artifacts/ingestion/duckdb_load_report.json`.

Script:

- [1_load_raw_to_duckdb.py](/Users/brunabianchi/Documents/home-credit-analytics-case-study/scripts/1_load_raw_to_duckdb.py)

## Metadados e auditoria

Cada execução da ingestão é registrada na schema `metadados` do DuckDB.

Tabelas atuais:

- `metadados.ingestion_runs`: resumo de cada execução;
- `metadados.ingestion_run_tables`: status de cada arquivo por execução;
- `metadados.source_schema_reference`: referência de colunas esperadas por arquivo de origem.

Esses registros permitem acompanhar:

- quando a ingestão foi executada;
- quais arquivos estavam disponíveis;
- quais arquivos foram lidos com sucesso;
- quais cargas técnicas foram realizadas;
- quais erros ocorreram.
