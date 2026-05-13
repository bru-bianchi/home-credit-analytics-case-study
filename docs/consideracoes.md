# Considerações Para Produção E Escalabilidade

O projeto atual é um case local, batch e reprodutível com DuckDB, Parquet e SQL versionado. Em produção, a arquitetura
deveria preservar a mesma separação lógica entre `raw`, `bronze`, `silver` e `gold`, mas evoluir os controles de escala,
resiliência e operação.

| Evolução | Por que importa em produção |
|---|---|
| Particionamento por fonte e data de ingestão | Reduz custo de leitura, habilita processamento incremental e melhora performance em volumes maiores |
| Data contracts | Evita que quebras de schema ou mudanças de significado cheguem às camadas analíticas sem validação |
| Quarentena ou DLQ de arquivos inválidos | Isola dados problemáticos sem interromper todo o pipeline |
| Orquestração com DAG, dependências e retries | Garante execução ordenada, reprocessamento controlado e recuperação mais simples de falhas |
| Lineage e observabilidade histórica | Ajuda a explicar de onde veio cada métrica e quando ela foi atualizada |
| Alertas automáticos | Reduz tempo de detecção para falhas de ingestão, schema drift e problemas de qualidade |
| Engine distribuída ou lakehouse cloud-native | Sustenta crescimento de volume, concorrência e ingestões mais frequentes |
| Versionamento externo de regras sensíveis | Permite governar thresholds, faixas e exceções de negócio com mais rastreabilidade |
| Políticas de lifecycle em storage | Controla custo sem perder histórico necessário para auditoria |

A implementação local já antecipa parte dessa disciplina com metadados, fingerprints, relatórios de execução e SQLs
versionados. O próximo salto para produção está menos na lógica analítica e mais na robustez operacional ao redor dela.
