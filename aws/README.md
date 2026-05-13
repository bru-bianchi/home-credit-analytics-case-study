# Proposta AWS

No arquivo `aws/main.tf` encontra-se a estrutura sugerida para uma pequena escala em produção desse projeto*. Os recursos
propostos são:

- `Amazon S3`: para storage dos arquivos raw, camada física do warehouse (parquet) e artefatos de execução do pipeline
- `Glue Job`: para execução dos scripts de validação raw e transformação bronze
- `Amazon Athena CTAS`: para construção das tabelas nas camadas Silver/Gold
- `AWS Glue Data Catalog`: para centralização do catálogo do warehouse
- `Amazon Athena`: para queries analíticas nas camadas Silver e, principalmente, Gold
- `Amazon EventBridge`: para agendamento do pipeline
- `AWS Step Functions State Machine`: para orquestração do pipeline em etapas
- `Amazon CloudWatch + SNS`: para monitoramento e alarmes de falhas no pipeline
- `Amazon QuickSight`: para criação de dashboards, conectado ao Athena, consultado a camada Gold

\* Para um processo de produção maior, outros recursos como `RedShift` (mais escalabilidade e estabilidade, view
materializadas, performance) e `Iceberg S3 Tables` (agilidade em inserção, reprodutibilidade, time travel).

