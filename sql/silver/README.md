# Silver SQL

Guarde aqui os SQLs versionados da camada `silver`.

Diretriz:
- os SQLs devem ser executáveis no DuckDB local;
- devem criar ou atualizar tabelas no schema `silver`;
- devem servir como fonte reprodutível do fluxo automatizado.

Modelo da camada:
- tabelas finais simples, derivadas das bases originais da `bronze`, com colunas tratadas e features simples;
- tabelas agregadas, derivadas das bases `silver`, com sufixo `_agg`.

Convenção sugerida:
- uma tabela original relevante pode virar uma tabela `silver` consolidada, como `applications`;
- tabelas agregadas devem deixar clara a granularidade no nome, como `installments_per_application_agg`.

Regras de nulos:
- por enquanto, o tratamento de nulos deve ficar explícito no próprio SQL com `COALESCE`, `CASE` e `NULLIF` quando houver justificativa analítica clara;
- quando não houver decisão de negócio validada, prefira manter `NULL` em vez de imputar artificialmente;
- evite depender de arquivos auxiliares externos para controlar imputações nesta fase inicial do projeto.
