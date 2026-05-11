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
│   ├── utils/
│   └── credit_risk_pipeline/
│       ├── raw/
│       ├── bronze/
│       ├── silver/
│       └── gold/
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

Baixe os arquivos do
dataset [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data)
e coloque os CSVs originais em `data/raw/`.

### 5. Execute o pipeline local

Atualmente, o pipeline é executado por camada via scripts em `scripts/`.

### 6. Etapas atuais do pipeline

O fluxo atual está organizado em macroetapas:

- `raw`: auditoria estrutural dos arquivos de entrada, geração de relatórios e persistência de metadados da camada.
  Veja [Ingestão raw](./docs/ingestao_raw.md).
- `bronze`: padronização técnica dos dados brutos, aplicação de mapping versionado, publicação em parquet e carga no
  schema `bronze` do warehouse local.
  Veja [Ingestão bronze](./docs/ingestao_bronze.md).
- `silver`: transformações analíticas em SQL, criação de tabelas base e agregadas, exportação em parquet e carga no
  schema `silver` do warehouse local.
  Veja [Ingestão silver](./docs/ingestao_silver.md).
- `warehouse e metadados`: centralização das camadas processadas e do histórico de execução no DuckDB local.
  Veja [Decisões de modelagem](./docs/decisoes_de_modelagem.md).
- `cache e reprocessamento incremental`: reaproveitamento por fingerprints e metadados para evitar processamento
  desnecessário entre execuções.
  Veja [Ingestão raw](./docs/ingestao_raw.md), [Ingestão bronze](./docs/ingestao_bronze.md) e
  [Ingestão silver](./docs/ingestao_silver.md).

Scripts atuais para execução por camada:

- `python scripts/0_run_raw_ingestion_audit.py`
- `python scripts/1_run_bronze_transformation.py`
- `python scripts/2_run_silver_transformation.py`

[Espaço reservado para o diagrama do fluxo de execução]

### 7. Explore o warehouse localmente

```bash
~/.duckdb/cli/1.4.4/duckdb data/warehouse/credit_risk.duckdb -ui
```

> Para instalar o DuckDB CLI e acessar o DuckDB UI, consulte a documentação oficial: [DuckDB Installation - CLI](https://duckdb.org/install/?platform=macos&environment=cli)

**Observação:** Garanta que o banco não esteja aberto em outra sessão do DuckDB enquanto o pipeline estiver rodando.


## Dashboard de métricas

- link AQUI e pequena explicação

## Documentação

A documentação detalhada está disponível em [`docs/`](./docs/), incluindo:

- [Arquitetura Técnica](./docs/arquitetura_tecnica.md)
- [Fontes de dados](docs/fontes_de_dados.md)
- [Decisões de modelagem](./docs/decisoes_de_modelagem.md)
- [Ingestão raw](./docs/ingestao_raw.md)
- [Ingestão bronze](./docs/ingestao_bronze.md)
- [Ingestão silver](./docs/ingestao_silver.md)
- [Regras de negócio](./docs/regras_de_negocio.md)

## Entregáveis previstos

- Pipeline de transformação em `Python` e `SQL`
- Documentação da modelagem
- Camadas `bronze`, `silver` e `gold` em `.parquet`
- Tabela analítica final em `.parquet`, otimizada para consumo analítico e modelagem
- Dashboard analítico, acessível online
- Infraestrutura como código (IaC) para a proposta em cloud AWS

## Considerações para Produção e Escalabilidade

Este projeto foi intencionalmente desenvolvido como um case local e batch-oriented de analytics engineering, utilizando
DuckDB e datasets estáticos. Algumas decisões arquiteturais voltadas para produção foram simplificadas para evitar
complexidade desnecessária no escopo atual.

Em um ambiente de produção com ingestão contínua e maiores volumes de dados, as seguintes evoluções poderiam ser
consideradas:

* Particionamento das camadas raw e bronze por source e timestamp de ingestão, permitindo processamento incremental,
  partition pruning, paralelismo e execução distribuída.
* Data contracts entre sistemas de origem e pipelines de ingestão para validação de schemas, colunas obrigatórias, tipos
  e regras de negócio esperadas antes do processamento.
* Dead Letter Queue (DLQ) e mecanismos de fail-safe para isolamento de arquivos corrompidos, inconsistentes ou inválidos
  sem interromper o restante do pipeline.
* Estratégias de multi-region fail-safe e disaster recovery para aumentar disponibilidade e resiliência em ambientes
  cloud.
* Alertas automáticos e notificações de falha para inconsistências, schema drift, falhas de ingestão ou problemas de
  qualidade de dados em qualquer etapa do pipeline, especialmente na camada raw.
* Orquestração e lineage mais avançados, incluindo grafos de dependência, execução incremental baseada em DAG e
  observabilidade histórica das execuções.
* Motores distribuídos de processamento, como Spark ou plataformas lakehouse cloud-native, para cenários com ingestão
  contínua ou datasets de grande escala.

A implementação atual já possui mecanismos de cache baseados em metadados e fingerprints para evitar reprocessamentos
desnecessários das camadas bronze, silver e gold.
