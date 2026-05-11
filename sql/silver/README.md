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
- as regras de imputação devem ser definidas em `docs/references/silver_null_handling_mapping.csv`;
- os SQLs da silver devem aplicar essas regras explicitamente com `COALESCE` ou `CASE`.

Formato esperado do mapping de nulos:
- `table_name`: tabela de entrada da regra
- `column_name`: coluna alvo
- `null_handling_rule`: por exemplo `leave_null`, `fill_constant`, `fill_expression`, `conditional_fill`
- `replacement_value`: valor de substituição quando a regra for `fill_constant`
- `condition_sql`: predicado opcional para regras condicionais
- `is_active`: se a regra deve ser aplicada no fluxo
- `justification`: racional da regra
