# Ingestão Raw

A camada `raw` é o ponto de entrada do pipeline. Ela preserva os CSVs originais do Kaggle e executa apenas auditoria
estrutural, sem alterar ou carregar os dados como tabelas analíticas.

## Resumo Executivo

| Decisão | Implementação | Benefício |
|---|---|---|
| Preservar a origem | CSVs mantidos em `data/raw/` | Auditoria, reprodutibilidade e reprocessamento |
| Não transformar dados na Raw | Sem casts, imputações ou regras de negócio | Mantém a fonte original intacta |
| Auditar estrutura mínima | Validação de existência, leitura, linhas, colunas e erros simples | Detecta problemas antes da Bronze |
| Persistir metadados | `metadados.raw_validation_events` no DuckDB | Histórico de execução e rastreabilidade |
| Evitar releitura desnecessária | Cache por fingerprint e versão da validação | Reduz tempo em reexecuções |

## Objetivo

Garantir que os arquivos de origem estejam disponíveis, legíveis e preservados como fonte auditável.

Na prática, a Raw responde a três necessidades:

- confirmar que todos os arquivos esperados existem;
- registrar a estrutura observada de cada CSV;
- manter um histórico de validação sem modificar o dado original.

## Validação Executada

A lista de arquivos esperados está em [Fontes de dados](./fontes_de_dados.md). Para cada arquivo, a auditoria estrutural
verifica:

- existência do arquivo;
- arquivo vazio;
- sucesso de leitura do CSV;
- quantidade de linhas;
- quantidade de colunas;
- nomes das colunas;
- erros estruturais simples, como linhas com número inconsistente de colunas.

Cada arquivo é classificado com status como `valid`, `invalid` ou `missing`.

A Raw não valida o schema de referência do dataset. Essa comparação fica na Bronze, onde o arquivo
`HomeCredit_columns_description.csv` é usado para orientar mapeamento e validação técnica.

## Execução E Observabilidade

Script de execução:

- [scripts/0_run_raw_ingestion_audit.py](../scripts/0_run_raw_ingestion_audit.py)

Módulos principais:

- `src/credit_risk_pipeline/raw/config.py`;
- `src/credit_risk_pipeline/raw/raw_files_validator.py`;
- `src/credit_risk_pipeline/raw/create_metadata.py`.

Saídas:

- `artifacts/ingestion/raw_ingestion_report.json`;
- eventos em `metadados.raw_validation_events`.

## Cache E Reprocessamento

A validação de um arquivo é reaproveitada quando o arquivo permanece inalterado.

Critérios de reaproveitamento:

- `file_fingerprint`, calculado a partir de caminho, tamanho em bytes e timestamp de modificação;
- `process_version`, que representa a versão atual da lógica de validação raw.

Quando ambos coincidem com uma validação anterior bem-sucedida, a leitura do CSV não é repetida e o arquivo é marcado
como reaproveitado.

## Limites Da Camada

A Raw não faz:

- carga analítica no warehouse;
- alteração dos arquivos originais;
- tratamento de nulos;
- casts;
- joins;
- criação de features;
- publicação de `bronze`, `silver` ou `gold`.

Esse limite mantém a origem preservada e desloca decisões técnicas ou analíticas para as camadas seguintes.
