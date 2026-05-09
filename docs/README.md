# Documentação

Esta pasta concentra a documentação técnica e funcional do projeto.

Conteúdo previsto:

- decisões de arquitetura;
- etapas de ingestão;
- modelagem e transformações;
- critérios de qualidade de dados;
- publicação e consumo analítico;
- proposta de infraestrutura em AWS.

## Status inicial

Os primeiros registros desta documentação irão cobrir:

- definição da ingestão em Python;
- detalhamento da ingestão inicial dos arquivos raw;
- uso do DuckDB como engine analítica local/de desenvolvimento;
- organização das camadas físicas `raw`, `bronze`, `silver` e `gold`;
- criação das tabelas e metadados no warehouse DuckDB para auditoria, queries e consumo analítico.
