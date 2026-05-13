# Documentação

Esta pasta concentra a documentação técnica e funcional do projeto de análise de risco de crédito.

## Como Ler

- [Arquitetura técnica](./arquitetura_tecnica.md): como o pipeline roda localmente.
- [Decisões de modelagem](./decisoes_de_modelagem.md): por que os dados foram organizados em camadas.
- [Fontes de dados](./fontes_de_dados.md): quais arquivos alimentam o projeto e qual papel têm na análise.
- [Ingestão raw](./ingestao_raw.md), [bronze](./ingestao_bronze.md), [silver](./ingestao_silver.md) e
  [gold](./ingestao_gold.md): o que cada etapa transforma, publica e entrega para a etapa seguinte.
- [Regras de negócio](./regras_de_negocio.md): principais sinais de risco criados e por que importam para o negócio.
- [Considerações para produção](./consideracoes.md): evoluções para escalar a solução fora do contexto local do case.

## Referências

A pasta [references](./references/) guarda arquivos auxiliares versionados, incluindo:

- dicionário de colunas original do Home Credit;
- mapeamentos de colunas e schema da camada `bronze`;
- regras explícitas de valores sentinela;
- regras de faixas usadas na camada `gold`.
