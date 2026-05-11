# Modelagem de Dados

Este documento consolida as decisões de organização dos dados do projeto, separando a camada física de arquivos da
camada lógica e analítica no DuckDB.

## Organização dos arquivos

Todos os dados do projeto ficam dentro de `data/`.

- `data/raw/`: arquivos CSV originais do Kaggle, mantidos intocados para reprodutibilidade
- `data/bronze/`: arquivos parquet com compressão snappy, derivados dos CSVs originais e com padronização técnica
  inicial, como nomes de colunas
- `data/silver/`: arquivos parquet com tratamento de nulos, inconsistências, enriquecimentos e tabelas detalhadas ou
  agregadas para análise histórica
- `data/gold/`: arquivos parquet finais, modelados para consumo analítico pronto, data marts, agregações flexíveis e
  tabela final de modelagem para ML
- `data/warehouse/`: banco local DuckDB com as tabelas de `bronze`, `silver` e `gold`, além de metadados e objetos
  auxiliares organizados para consultas

Resumo da arquitetura:

- Parquet em `bronze`, `silver` e `gold` = camada física de armazenamento.
- DuckDB em `warehouse` = camada lógica e analítica para exploração, joins, queries e consumo por negócio.

Para detalhes sobre as tabelas de origem consideradas no projeto, consulte [fontes_de_dados.md](/Users/brunabianchi/Documents/home-credit-analytics-case-study/docs/fontes_de_dados.md).

## Papel de cada camada

### RAW

> Objetivo: preservar a origem como exatamente recebida.

- Contém os `CSV`s originais
- Serve como ponto de reprocessamento do pipeline
- Não recebe correções nem transformações
- É a camada de entrada para execução do pipeline a partir dos arquivos originais

### BRONZE

> Objetivo: criar uma primeira versão técnica, consistente e eficiente para leitura.

- Conversão de CSV para `parquet com compressão snappy`
- Padronização de nomes de colunas
- Ajustes técnicos mínimos de schema e tipos
- Ponto natural para futuras validações contra schema de referência
- Sem aplicação de regras de negócio complexas

O formato `parquet` é preferido nessa camada porque:

- Preserva melhor o schema
- Melhora performance de leitura analítica
- Reduz espaço em disco
- Reduz problemas típicos de CSV, como parsing, encoding e inferência inconsistente

### SILVER

> Objetivo: consolidar dados confiáveis e enriquecidos para consumo analítico detalhado e histórico.

- Tratamento de nulos, duplicidades e inconsistências
- Joins entre tabelas
- Aplicação de regras de negócio
- Criação de features e atributos derivados
- Harmonização de granularidade e relacionamento entre entidades
- Tabelas base e tabelas agregadas `_agg` para exploração analítica em diferentes granularidades
- Camada esperada de consumo para análises mais detalhadas, históricas e investigativas

### GOLD

> Objetivo: disponibilizar conjuntos finais prontos para consumo, distribuição e modelagem.

- Tabelas finais otimizadas para queries recorrentes
- Saídas voltadas a BI, dashboards e consumo de negócio
- Data marts e agregações mais prontas para uso
- Tabelas analíticas flexíveis para consumo final
- Tabela final de modelagem para ML
- Possibilidade de modelos dimensionais, fatos, dimensões e tabelas analíticas finais

## Modelagem do warehouse

Dentro de `data/warehouse/credit_risk.duckdb`, o banco local deve centralizar:

- Tabelas das camadas `bronze`, `silver` e `gold`
- Metadados de ingestão e transformação para auditoria
- Estruturas auxiliares para consultas e exploração local

Organização lógica esperada no DuckDB:

- Schema `bronze`: tabelas técnicas padronizadas a partir dos arquivos em parquet da camada bronze
- Schema `silver`: tabelas tratadas, enriquecidas e agregadas para análise detalhada e histórica
- Schema `gold`: tabelas finais para consumo pronto, marts e base final de ML
- Schema `metadados`: histórico de execuções, auditoria e referências de schema

**Observação:** a ingestão inicial atualmente ainda valida e carrega os CSVs de `data/raw/` como etapa de bootstrap
técnico do projeto. A evolução natural do pipeline é publicar e consumir as camadas analíticas a partir dos parquets de
`bronze`, `silver` e `gold`.

## Fluxo de dados esperado

O fluxo do projeto é:

1. Receber os arquivos originais em `data/raw/`
2. Validar existência, leitura e estrutura básica dos arquivos
3. Publicar os arquivos padronizados em `data/bronze/`
4. Aplicar tratamentos e enriquecimentos em `data/silver/`
5. Materializar tabelas finais, marts e saídas de modelagem em `data/gold/`
6. Carregar ou sincronizar `bronze`, `silver` e `gold` no DuckDB em `data/warehouse/`
7. Disponibilizar as tabelas para queries, dashboard, consumo analítico e modelagem

## Detalhamento das ingestões

A explicação operacional detalhada da ingestão inicial e transformação para outras camadas foram separadas em documentos
próprios. 

- [Ingestão raw](./ingestao_raw.md)
- [Ingestão bronze](./ingestao_bronze.md)
- [Ingestão silver](./ingestao_silver.md)
