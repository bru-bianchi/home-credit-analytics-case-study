# Análise de Risco de Crédito

Projeto de analytics engineering baseado no
dataset [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data), com foco em
ingestão de dados, modelagem
analítica, criação de features, análise de negócio e estruturação de uma visão para dashboard.

## Contexto

Esse projeto tem como proposta a estruturação de uma camada analítica de risco de crédito que permita que o time de
Produto de Plataforma de Crédito seja capaz de extrair insights dos dados disponíveis de forma fácil e otimizada,
acompanhar métricas importantes para o negócio e facilitar a tomada de decisão embasada em informações reais, bem como
utilizar as bases para criação de modelos estatísticos e análises favoráveis ao negócio.

**Objetivo principal de negócio:** Analisar padrões de inadimplência

## Escopo

- Ingestão das bases de origem
- Modelagem da camada de dados organizada
- Tratamento de inconsistências e dados ausentes
- Criação de atributos derivados relevantes para risco
- Consolidação de uma tabela analítica final
- Construção de um dashboard online com insights relevantes ao negócio
- Definição de uma proposta de infraestrutura em AWS com Terraform

**O que NÃO faz parte do escopo:**

- Criação, treinamento e acompanhamento de modelos de *Machine Learning*

## Estrutura do repositório

```text
.
├── README.md
├── data/
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   └── warehouse/
├── docs/
├── scripts/
├── src/
└── cloud_infra/
    └── terraform/
```

## Como começar

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd home-credit-analytics-case-study
```

### 2. Crie e ative um ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Adicione os dados brutos

Baixe os arquivos do dataset [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data)
e coloque os CSVs originais em `data/raw/`.

### 5. Execute o pipeline local

```bash
python src/run_all.py
```

Esse será o entrypoint principal do pipeline local, consolidando as etapas disponíveis do projeto.

### 6. Etapas atuais do pipeline

Atualmente, o fluxo disponível contempla:

- auditoria inicial dos arquivos raw, com geração de `artifacts/ingestion/raw_ingestion_report.json`;
- carga técnica no DuckDB local, com geração de `artifacts/ingestion/duckdb_load_report.json`;
- criação ou atualização do banco local em `data/warehouse/credit_risk.duckdb`.

### 7. Explore o warehouse localmente

Para instalar o DuckDB CLI e acessar o DuckDB UI, consulte a documentação oficial:

- [DuckDB Installation - CLI](https://duckdb.org/install/?platform=macos&environment=cli)

**Observação:** Garanta que o banco não esteja aberto em outra sessão do DuckDB enquanto a ingestão estiver rodando.

```bash
~/.duckdb/cli/1.4.4/duckdb data/warehouse/credit_risk.duckdb -ui
```

## Dashboard de métricas

- link AQUI e pequena explicação

## Documentação

A documentação detalhada está disponível em [`docs/`](./docs/), incluindo:

- [Stack Técnica](./docs/stack.md)
- [Fontes de dados](docs/fontes_de_dados.md)
- [Decisões de modelagem](./docs/decisoes_de_modelagem.md)
- [Ingestão raw](./docs/ingestao_raw.md)
- [Regras de negócio](./docs/regras_de_negocio.md)

## Entregáveis previstos

- Pipeline de transformação em `Python` e `SQL`
- Documentação da modelagem
- Camadas `bronze`, `silver` e `gold` em `.parquet`
- Tabela analítica final em `.parquet`, otimizada para consumo analítico e modelagem
- Dashboard analítico, acessível online
- Infraestrutura como código (IaC) para a proposta em cloud AWS
