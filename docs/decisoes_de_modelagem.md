# Ingestão de Dados Raw

Este documento descreve de forma simples a primeira etapa do projeto: checagem, processamento inicial e ingestão dos
arquivos `raw`.

## Objetivo

Garantir que os arquivos de origem estejam disponíveis, possam ser lidos corretamente e sejam carregados para o ambiente
analítico local sem aplicar regras de negócio ou transformações analíticas.

## Escopo desta etapa

Nesta etapa, o processo faz apenas o necessário para preparar os dados para as próximas camadas do projeto.

Inclui:

- verificar se os arquivos esperados existem em `data/raw/`;
- validar se os arquivos podem ser lidos em Python;
- identificar estrutura básica de cada arquivo;
- registrar metadados da leitura;
- carregar os arquivos válidos para a camada `raw` no DuckDB.

Não inclui:

- tratamento de dados ausentes;
- correção de inconsistências de negócio;
- deduplicação analítica;
- criação de atributos derivados;
- joins entre tabelas.

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

## Etapa 1: check dos arquivos

O primeiro passo é uma auditoria simples dos arquivos `raw`.

Essa auditoria verifica:

- se o arquivo existe;
- se o arquivo está vazio;
- se a leitura do CSV funciona;
- quantidade de linhas;
- quantidade de colunas;
- nomes das colunas;
- tipos inferidos de forma básica;
- erros estruturais simples, como linhas com número inconsistente de colunas.

Além disso, a auditoria compara as colunas encontradas com uma referência versionada do projeto, derivada do arquivo:

- [docs/references/HomeCredit_columns_description.csv](/Users/brunabianchi/Documents/home-credit-analytics-case-study/docs/references/HomeCredit_columns_description.csv)

Essa checagem classifica o schema de cada arquivo como:

- `ok`: estrutura esperada;
- `warning`: colunas esperadas ausentes ou colunas extras, sem quebra crítica;
- `error`: ausência de colunas obrigatórias, impedindo a carga para `raw`.

Saída gerada:

- `artifacts/ingestion/raw_ingestion_report.json`

Script:

- [scripts/0_run_raw_ingestion_audit.py](/Users/brunabianchi/Documents/home-credit-analytics-case-study/scripts/0_run_raw_ingestion_audit.py)

## Etapa 2: processamento inicial

Depois da checagem, os arquivos que passaram na leitura são considerados aptos para ingestão.

Neste momento, o processamento ainda é mínimo e técnico:

- leitura em Python;
- validação básica da estrutura;
- separação entre arquivos válidos e arquivos com erro.

O objetivo aqui não é transformar os dados, mas apenas garantir que a camada `raw` seja carregada com segurança.

## Etapa 3: ingestão no DuckDB

Os arquivos válidos são carregados via Python para o banco local DuckDB, na schema `raw`.

Exemplo de destino:

- `raw.application_train`
- `raw.bureau`
- `raw.previous_application`

Essa carga é uma ingestão técnica. As transformações analíticas e a modelagem serão feitas depois, em SQL no DuckDB.

Antes de carregar um arquivo, o processo consulta o histórico de ingestões para verificar se aquele mesmo `raw` já foi processado com sucesso anteriormente. Nesta versão, a checagem usa o caminho do arquivo e seu tamanho em bytes.

Com isso, reexecuções do pipeline não recarregam automaticamente o mesmo arquivo, evitando duplicatas por rerun acidental.

Saída gerada:

- banco local em `data/warehouse/credit_risk.duckdb`
- relatório em `artifacts/ingestion/duckdb_load_report.json`

Script:

- [scripts/1_load_raw_to_duckdb.py](/Users/brunabianchi/Documents/home-credit-analytics-case-study/scripts/1_load_raw_to_duckdb.py)

## Registro de metadados

Cada execução da ingestão é registrada na schema `metadados` do DuckDB.

Tabelas atuais:

- `metadados.ingestion_runs`: resumo de cada execução;
- `metadados.ingestion_run_tables`: status de cada arquivo por execução.
- `metadados.source_schema_reference`: referência de colunas esperadas por arquivo de origem.

Esses registros permitem acompanhar:

- quando a ingestão foi executada;
- quais arquivos estavam disponíveis;
- quais arquivos foram lidos com sucesso;
- quais tabelas foram carregadas;
- quais erros ocorreram.

## Como visualizar o DuckDB localmente

O banco local gerado pela ingestão pode ser explorado tanto via linha de comando quanto por interface gráfica local.

Arquivo principal do banco:

- `data/warehouse/credit_risk.duckdb`

### DuckDB UI

O `DuckDB UI` pode ser utilizado para navegar pelas schemas, visualizar tabelas, colunas, tipos e executar queries
localmente em uma interface web.

Referência oficial:

- [The DuckDB Local UI](https://duckdb.org/2025/03/12/duckdb-ui)

Após instalar o DuckDB CLI, execute:

```bash
duckdb data/warehouse/credit_risk.duckdb -ui
```

Esse comando abre a interface local no navegador e permite:

- identificar schemas como `raw` e `metadados`;
- visualizar tabelas e colunas;
- inspecionar amostras dos dados;
- executar queries SQL diretamente sobre o banco local.

### DuckDB CLI

Para instalar o DuckDB CLI, siga a referência oficial e adapte o método conforme o sistema operacional utilizado:

- [DuckDB Installation - CLI](https://duckdb.org/install/?platform=macos&environment=cli)

Uma opção simples de instalação via terminal é:

```bash
curl https://install.duckdb.org | DUCKDB_VERSION=1.4.4 sh
```

Exemplos de consultas úteis:

```sql
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;
```

```sql
SELECT table_schema, table_name
FROM information_schema.tables
ORDER BY table_schema, table_name;
```

```sql
SELECT *
FROM metadados.ingestion_runs
ORDER BY started_at_utc DESC;
```

## Resumo da abordagem

De forma resumida, o fluxo atual é:

1. verificar os arquivos em `data/raw/`;
2. validar leitura e estrutura básica em Python;
3. registrar metadados da leitura;
4. carregar arquivos válidos para `raw` no DuckDB;
5. usar o DuckDB depois para modelagem e transformação.
