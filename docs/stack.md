# Stack Técnica

Escolhas técnicas utilizadas

## Nota de arquitetura

- O `DuckDB` foi escolhido neste projeto como engine analítica local e de desenvolvimento.
- Para uma solução mais robusta e contínua, com bases atualizadas recorrentemente, a arquitetura alvo será reavaliada na
  etapa de proposta em AWS, incluindo práticas de produção e infraestrutura como código.
- Como proposta de produção, a arquitetura alvo deverá evoluir para um modelo baseado em `data lake` ou `lakehouse`,
  garantindo maior estruturação dos dados, histórico, escalabilidade e melhor suporte a cargas recorrentes.
