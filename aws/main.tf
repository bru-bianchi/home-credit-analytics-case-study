terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix             = "${var.project_name}-${var.environment}"
  data_bucket_name        = coalesce(var.data_bucket_name, "${local.name_prefix}-data-${data.aws_caller_identity.current.account_id}")
  athena_results_location = "s3://${aws_s3_bucket.data.bucket}/athena-results/"

  default_silver_ctas_sql = <<-SQL
    CREATE TABLE IF NOT EXISTS ${aws_glue_catalog_database.silver.name}.silver_pipeline_placeholder
    WITH (
      format = 'PARQUET',
      external_location = 's3://${aws_s3_bucket.data.bucket}/silver/pipeline_placeholder/'
    ) AS
    SELECT 1 AS placeholder_id
  SQL

  default_gold_ctas_sql = <<-SQL
    CREATE TABLE IF NOT EXISTS ${aws_glue_catalog_database.gold.name}.${var.quicksight_gold_table_name}
    WITH (
      format = 'PARQUET',
      external_location = 's3://${aws_s3_bucket.data.bucket}/gold/${var.quicksight_gold_table_name}/'
    ) AS
    SELECT 1 AS placeholder_id
  SQL

  silver_ctas_sql = coalesce(var.silver_ctas_sql, local.default_silver_ctas_sql)
  gold_ctas_sql   = coalesce(var.gold_ctas_sql, local.default_gold_ctas_sql)
}

# S3 data lake:
# - raw: arquivos CSV originais
# - bronze/silver/gold: camada fisica do warehouse em Parquet
# - artifacts/logs: relatorios, auditoria e saidas tecnicas do pipeline
# - athena-results: resultados de queries Athena
resource "aws_s3_bucket" "data" {
  bucket = local.data_bucket_name

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Layer       = "data-lake"
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_object" "prefixes" {
  for_each = toset([
    "raw/",
    "bronze/",
    "silver/",
    "gold/",
    "artifacts/",
    "logs/",
    "scripts/",
    "athena-results/",
  ])

  bucket  = aws_s3_bucket.data.id
  key     = each.value
  content = ""
}

# Glue Data Catalog: catalogo central do warehouse/lakehouse.
resource "aws_glue_catalog_database" "raw" {
  name        = "${local.name_prefix}_raw"
  description = "Catalogo dos arquivos raw do pipeline ${var.project_name}."
}

resource "aws_glue_catalog_database" "bronze" {
  name        = "${local.name_prefix}_bronze"
  description = "Catalogo da camada Bronze em Parquet."
}

resource "aws_glue_catalog_database" "silver" {
  name        = "${local.name_prefix}_silver"
  description = "Catalogo da camada Silver em Parquet."
}

resource "aws_glue_catalog_database" "gold" {
  name        = "${local.name_prefix}_gold"
  description = "Catalogo da camada Gold em Parquet para consumo analitico e BI."
}

# IAM do Glue Job.
resource "aws_iam_role" "glue_job" {
  name = "${local.name_prefix}-glue-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_job.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_data_access" {
  name = "${local.name_prefix}-glue-data-access"
  role = aws_iam_role.glue_job.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data.arn,
          "${aws_s3_bucket.data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:BatchCreatePartition",
          "glue:BatchDeletePartition",
          "glue:BatchGetPartition",
          "glue:GetPartitions"
        ]
        Resource = "*"
      }
    ]
  })
}

# Glue Jobs:
# Os scripts devem ser publicados no S3, por exemplo:
# s3://<bucket>/scripts/glue/raw_validation.py
# s3://<bucket>/scripts/glue/bronze_transformation.py
resource "aws_glue_job" "raw_validation" {
  name              = "${local.name_prefix}-raw-validation"
  role_arn          = aws_iam_role.glue_job.arn
  glue_version      = var.glue_version
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.data.bucket}/${var.raw_validation_script_key}"
  }

  default_arguments = {
    "--TempDir"                          = "s3://${aws_s3_bucket.data.bucket}/artifacts/glue-temp/"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--DATA_BUCKET"                      = aws_s3_bucket.data.bucket
    "--RAW_PREFIX"                       = "raw/"
    "--ARTIFACTS_PREFIX"                 = "artifacts/raw/"
    "--RAW_DATABASE"                     = aws_glue_catalog_database.raw.name
  }
}

resource "aws_glue_job" "bronze_transformation" {
  name              = "${local.name_prefix}-bronze-transformation"
  role_arn          = aws_iam_role.glue_job.arn
  glue_version      = var.glue_version
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.data.bucket}/${var.bronze_transformation_script_key}"
  }

  default_arguments = {
    "--TempDir"                          = "s3://${aws_s3_bucket.data.bucket}/artifacts/glue-temp/"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-glue-datacatalog"          = "true"
    "--DATA_BUCKET"                      = aws_s3_bucket.data.bucket
    "--RAW_PREFIX"                       = "raw/"
    "--BRONZE_PREFIX"                    = "bronze/"
    "--ARTIFACTS_PREFIX"                 = "artifacts/bronze/"
    "--RAW_DATABASE"                     = aws_glue_catalog_database.raw.name
    "--BRONZE_DATABASE"                  = aws_glue_catalog_database.bronze.name
  }
}

# Athena para CTAS Silver/Gold e queries analiticas.
resource "aws_athena_workgroup" "analytics" {
  name = "${local.name_prefix}-analytics"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = local.athena_results_location
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_athena_named_query" "silver_ctas" {
  name        = "${local.name_prefix}-build-silver"
  description = "CTAS para materializacao da camada Silver."
  database    = aws_glue_catalog_database.bronze.name
  workgroup   = aws_athena_workgroup.analytics.name
  query       = local.silver_ctas_sql
}

resource "aws_athena_named_query" "gold_ctas" {
  name        = "${local.name_prefix}-build-gold"
  description = "CTAS para materializacao da camada Gold."
  database    = aws_glue_catalog_database.silver.name
  workgroup   = aws_athena_workgroup.analytics.name
  query       = local.gold_ctas_sql
}

# Step Functions: orquestracao sequencial do pipeline.
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/vendedlogs/states/${local.name_prefix}-pipeline"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role" "step_functions" {
  name = "${local.name_prefix}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions" {
  name = "${local.name_prefix}-step-functions-policy"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions",
          "glue:CreateTable",
          "glue:UpdateTable"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data.arn,
          "${aws_s3_bucket.data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${local.name_prefix}-pipeline"
  role_arn = aws_iam_role.step_functions.arn
  type     = "STANDARD"

  logging_configuration {
    include_execution_data = true
    level                  = "ERROR"
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
  }

  definition = jsonencode({
    Comment = "Pipeline Home Credit Analytics: raw validation, bronze Glue job, Silver CTAS e Gold CTAS."
    StartAt = "RawValidation"
    States = {
      RawValidation = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.raw_validation.name
        }
        Next = "BronzeTransformation"
      }
      BronzeTransformation = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.bronze_transformation.name
        }
        Next = "BuildSilver"
      }
      BuildSilver = {
        Type     = "Task"
        Resource = "arn:aws:states:::athena:startQueryExecution.sync"
        Parameters = {
          QueryString = local.silver_ctas_sql
          WorkGroup   = aws_athena_workgroup.analytics.name
          QueryExecutionContext = {
            Database = aws_glue_catalog_database.bronze.name
          }
          ResultConfiguration = {
            OutputLocation = local.athena_results_location
          }
        }
        Next = "BuildGold"
      }
      BuildGold = {
        Type     = "Task"
        Resource = "arn:aws:states:::athena:startQueryExecution.sync"
        Parameters = {
          QueryString = local.gold_ctas_sql
          WorkGroup   = aws_athena_workgroup.analytics.name
          QueryExecutionContext = {
            Database = aws_glue_catalog_database.silver.name
          }
          ResultConfiguration = {
            OutputLocation = local.athena_results_location
          }
        }
        Next = "PipelineSucceeded"
      }
      PipelineSucceeded = {
        Type = "Succeed"
      }
    }
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# EventBridge Scheduler: agenda a execucao da state machine.
resource "aws_iam_role" "scheduler" {
  name = "${local.name_prefix}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "scheduler.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${local.name_prefix}-scheduler-policy"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "states:StartExecution"
        Resource = aws_sfn_state_machine.pipeline.arn
      }
    ]
  })
}

resource "aws_scheduler_schedule" "pipeline" {
  name                         = "${local.name_prefix}-pipeline-schedule"
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = var.schedule_timezone
  state                        = var.enable_schedule ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.pipeline.arn
    role_arn = aws_iam_role.scheduler.arn
    input = jsonencode({
      source      = "eventbridge-scheduler"
      project     = var.project_name
      environment = var.environment
    })
  }
}

# Monitoramento: SNS + alarme para falhas da state machine.
resource "aws_sns_topic" "pipeline_alerts" {
  name = "${local.name_prefix}-pipeline-alerts"
}

resource "aws_sns_topic_subscription" "pipeline_alert_email" {
  count     = var.alert_email == null ? 0 : 1
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "pipeline_failed" {
  alarm_name          = "${local.name_prefix}-pipeline-failed"
  alarm_description   = "Alarme para falhas na Step Functions State Machine do pipeline."
  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.pipeline.arn
  }

  alarm_actions = [aws_sns_topic.pipeline_alerts.arn]
  ok_actions    = [aws_sns_topic.pipeline_alerts.arn]
}

# QuickSight:
# Cria a fonte Athena e um dataset inicial sobre uma tabela Gold.
# O dashboard visual pode ser criado no QuickSight a partir deste dataset ou
# promovido via template em uma etapa posterior.
resource "aws_quicksight_data_source" "athena" {
  count = var.create_quicksight_assets ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_source_id = "${local.name_prefix}-athena"
  name           = "${local.name_prefix}-athena"
  type           = "ATHENA"

  parameters {
    athena {
      work_group = aws_athena_workgroup.analytics.name
    }
  }

  ssl_properties {
    disable_ssl = false
  }
}

resource "aws_quicksight_data_set" "gold" {
  count = var.create_quicksight_assets ? 1 : 0

  aws_account_id = data.aws_caller_identity.current.account_id
  data_set_id    = "${local.name_prefix}-gold-${var.quicksight_gold_table_name}"
  name           = "${local.name_prefix}-gold-${var.quicksight_gold_table_name}"
  import_mode    = "SPICE"

  physical_table_map {
    physical_table_map_id = "gold_table"

    relational_table {
      data_source_arn = aws_quicksight_data_source.athena[0].arn
      catalog         = "AwsDataCatalog"
      schema          = aws_glue_catalog_database.gold.name
      name            = var.quicksight_gold_table_name

      dynamic "input_columns" {
        for_each = var.quicksight_gold_columns

        content {
          name = input_columns.value.name
          type = input_columns.value.type
        }
      }
    }
  }
}

variable "aws_region" {
  description = "Regiao AWS onde os recursos serao criados."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome base do projeto."
  type        = string
  default     = "home-credit-analytics"
}

variable "environment" {
  description = "Ambiente de deploy."
  type        = string
  default     = "prod"
}

variable "data_bucket_name" {
  description = "Nome do bucket S3. Se nulo, sera gerado com project/environment/account."
  type        = string
  default     = null
}

variable "raw_validation_script_key" {
  description = "Chave S3 do script Glue para validacao raw."
  type        = string
  default     = "scripts/glue/raw_validation.py"
}

variable "bronze_transformation_script_key" {
  description = "Chave S3 do script Glue para transformacao bronze."
  type        = string
  default     = "scripts/glue/bronze_transformation.py"
}

variable "glue_version" {
  description = "Versao do AWS Glue usada nos jobs."
  type        = string
  default     = "4.0"
}

variable "glue_worker_type" {
  description = "Tipo de worker dos Glue Jobs."
  type        = string
  default     = "G.1X"
}

variable "glue_number_of_workers" {
  description = "Numero de workers dos Glue Jobs."
  type        = number
  default     = 2
}

variable "silver_ctas_sql" {
  description = "SQL Athena CTAS para construcao da camada Silver. Se nulo, usa placeholder."
  type        = string
  default     = null
}

variable "gold_ctas_sql" {
  description = "SQL Athena CTAS para construcao da camada Gold. Se nulo, usa placeholder."
  type        = string
  default     = null
}

variable "schedule_expression" {
  description = "Expressao de agendamento do EventBridge Scheduler."
  type        = string
  default     = "cron(0 7 * * ? *)"
}

variable "schedule_timezone" {
  description = "Timezone do agendamento."
  type        = string
  default     = "America/Sao_Paulo"
}

variable "enable_schedule" {
  description = "Define se o agendamento do pipeline inicia habilitado."
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "E-mail para receber alertas SNS. Se nulo, nao cria subscription."
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "Retencao dos logs da Step Functions no CloudWatch."
  type        = number
  default     = 30
}

variable "create_quicksight_assets" {
  description = "Cria data source e dataset QuickSight conectados ao Athena."
  type        = bool
  default     = true
}

variable "quicksight_gold_table_name" {
  description = "Tabela Gold usada como dataset inicial do QuickSight."
  type        = string
  default     = "fact_credit_risk"
}

variable "quicksight_gold_columns" {
  description = "Colunas da tabela Gold usadas pelo dataset QuickSight. Ajustar para o schema real."
  type = list(object({
    name = string
    type = string
  }))
  default = [
    {
      name = "placeholder_id"
      type = "INTEGER"
    }
  ]
}

output "data_bucket" {
  description = "Bucket S3 principal do data lake."
  value       = aws_s3_bucket.data.bucket
}

output "glue_databases" {
  description = "Databases criados no Glue Data Catalog."
  value = {
    raw    = aws_glue_catalog_database.raw.name
    bronze = aws_glue_catalog_database.bronze.name
    silver = aws_glue_catalog_database.silver.name
    gold   = aws_glue_catalog_database.gold.name
  }
}

output "athena_workgroup" {
  description = "Workgroup Athena para CTAS e queries analiticas."
  value       = aws_athena_workgroup.analytics.name
}

output "step_functions_state_machine_arn" {
  description = "ARN da State Machine que orquestra o pipeline."
  value       = aws_sfn_state_machine.pipeline.arn
}

output "sns_alert_topic_arn" {
  description = "Topico SNS usado para alertas do pipeline."
  value       = aws_sns_topic.pipeline_alerts.arn
}
