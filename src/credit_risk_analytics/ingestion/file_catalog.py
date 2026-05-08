"""List of raw files expected by the project."""

RAW_TABLES = [
    {
        "table_name": "application_train",
        "file_name": "application_train.csv",
        "required_columns": ["SK_ID_CURR", "TARGET"],
    },
    {
        "table_name": "application_test",
        "file_name": "application_test.csv",
        "required_columns": ["SK_ID_CURR"],
    },
    {
        "table_name": "bureau",
        "file_name": "bureau.csv",
        "required_columns": ["SK_ID_CURR", "SK_BUREAU_ID"],
    },
    {
        "table_name": "bureau_balance",
        "file_name": "bureau_balance.csv",
        "required_columns": ["SK_BUREAU_ID", "MONTHS_BALANCE"],
    },
    {
        "table_name": "previous_application",
        "file_name": "previous_application.csv",
        "required_columns": ["SK_ID_PREV", "SK_ID_CURR"],
    },
    {
        "table_name": "pos_cash_balance",
        "file_name": "POS_CASH_balance.csv",
        "required_columns": ["SK_ID_PREV", "SK_ID_CURR"],
    },
    {
        "table_name": "credit_card_balance",
        "file_name": "credit_card_balance.csv",
        "required_columns": ["SK_ID_PREV", "SK_ID_CURR"],
    },
    {
        "table_name": "installments_payments",
        "file_name": "installments_payments.csv",
        "required_columns": ["SK_ID_PREV", "SK_ID_CURR"],
    },
]
