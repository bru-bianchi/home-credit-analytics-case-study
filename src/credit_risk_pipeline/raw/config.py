"""Shared configuration for raw ingestion validation."""


RAW_VALIDATION_VERSION = "raw_validation_v1"

RAW_TABLES = [
    {
        "table_name": "application_train",
        "file_name": "application_train.csv",
    },
    {
        "table_name": "application_test",
        "file_name": "application_test.csv",
    },
    {
        "table_name": "bureau",
        "file_name": "bureau.csv",
    },
    {
        "table_name": "bureau_balance",
        "file_name": "bureau_balance.csv",
    },
    {
        "table_name": "previous_application",
        "file_name": "previous_application.csv",
    },
    {
        "table_name": "pos_cash_balance",
        "file_name": "POS_CASH_balance.csv",
    },
    {
        "table_name": "credit_card_balance",
        "file_name": "credit_card_balance.csv",
    },
    {
        "table_name": "installments_payments",
        "file_name": "installments_payments.csv",
    },
]
