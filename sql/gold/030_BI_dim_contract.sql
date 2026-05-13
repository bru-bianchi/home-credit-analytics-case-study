CREATE OR REPLACE TABLE gold.dim_contract AS

-- Uma linha por sk_id_curr: características do contrato atual

SELECT
    ROW_NUMBER() OVER (ORDER BY sk_id_curr) AS contract_key,
    sk_id_curr,

    -- Produto atual
    name_contract_type,
    flag_cash_loan,
    flag_revolving_loan,
    flag_consumer_loan,

    -- Completudo de informação
    flag_social_default_na

FROM silver.applications
;
