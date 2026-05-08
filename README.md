# Análise de Risco de Crédito

Projeto de analytics engineering baseado no dataset [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data), com foco em ingestão de dados, modelagem
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
│   └── warehouse/
├── docs/
├── scripts/
├── src/
└── cloud_infra/
    └── terraform/
```

## Como começar

- clone o repositorio
- criar venv
- instalar requirements
- baixar os dados do kaggle e colocar em data/raw/
- instruções para rodar localmente 

```bash 
python src/run_all.py
```

- instruções para visualizar os dados localmente e fazer queries, se necessário

```bash
duckdb data/warehouse/credit_risk.duckdb -ui
```

## Dashboard de métricas

- link AQUI e pequena explicação

## Documentação

A documentação detalhada está disponível em [`docs/`](./docs/), incluindo:

- [Stack Técnica](./docs/stack.md)
- [Fontes de dados](./docs/dados.md)
- [Decisões de modelagem](./docs/decisoes_de_modelagem.md)
- [Regras de negócio](./docs/regras_de_negocio.md)


## Entregáveis previstos

- Pipeline de transformação em `Python` e `SQL`
- Documentação da modelagem
- Tabela analítica final em `.parquet`
- Dashboard analítico, acessível online
- Infraestrutura como código (IaC) para a proposta em cloud AWS
