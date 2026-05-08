# Análise de Risco de Crédito

## Introdução

Esse projeto tem como proposta a estruturação de uma camada analítica de risco de crédito que permita que o time de
Produto de Plataforma de Crédito seja capaz, de forma fácil e otimizada, a extrair insights dos dados disponíveis,
acompanhar métricas importantes para o negócio e facilitar a tomada de decisão embasada em informações reais, bem como
utilizar as bases para criação de modelos estatísticos e análises favoráveis ao negócio.

**Objetivo principal de negócio:** Analisar padrões de inadimplência

## Fontes de dados

Fonte principal:

- Kaggle: [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data)

Tabelas `raw` previstas no escopo inicial:

- `application_train.csv`: dados de aplicações de crédito com variável *target*
- `application_test.csv`: dados de aplicações de crédito sem variável *target* - base de teste
- `bureau.csv`: histórico de crédito externo (em outras instituições)
- `bureau_balance.csv`: status mensal do histórico de crédito externo
- `previous_application.csv`: histórico de aplicações anteriores
- `POS_CASH_balance.csv`: histórico de empréstimos do tipo POS (parcelamento) e empréstimos em espécie
- `credit_card_balance.csv`: histórico de cartão de crédito
- `installments_payments.csv`: histórico de pagamentos parcelados

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

## Entregáveis previstos

- Pipeline de transformação em `Python` e `SQL`
- Documentação da modelagem
- Tabela analítica final em `.parquet`
- Dashboard analítico, acessível online
- Infraestrutura como código (IaC) para a proposta em cloud AWS

## Estrutura de referência

```text
.
├── README.md
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
├── sql/
├── src/
├── dashboards/
├── docs/
└── infra/
    └── terraform/
```

## Visão geral da pasta data

- `data/raw/`: arquivos originais recebidos da fonte, mantidos intocados.
- `data/warehouse/`: arquivo DuckDB local com as camadas analíticas do projeto.

Para informações detalhadas, consulte `docs/organizacao_de_dados.md`

## Nota de arquitetura

- O `DuckDB` foi escolhido neste projeto como engine analítica local e de desenvolvimento.
- Para uma solução mais robusta e contínua, com bases atualizadas recorrentemente, a arquitetura alvo será reavaliada na
  etapa de proposta em AWS, incluindo práticas de produção e infraestrutura como código.
- Como proposta de produção, a arquitetura alvo deverá evoluir para um modelo baseado em `data lake` ou `lakehouse`,
  garantindo maior estruturação dos dados, histórico, escalabilidade e melhor suporte a cargas recorrentes.
