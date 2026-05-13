CREATE OR REPLACE TABLE gold.ref_band_rules AS

-- Regras auditáveis de faixas usadas na Gold ML e nas dimensões BI
-- Origem: docs/references/gold_band_rules.csv

SELECT
    band_group::VARCHAR AS band_group,
    source_column::VARCHAR AS source_column,
    band_order::INTEGER AS band_order,
    band_label::VARCHAR AS band_label,
    lower_bound::DOUBLE AS lower_bound,
    upper_bound::DOUBLE AS upper_bound,
    lower_inclusive::BOOLEAN AS lower_inclusive,
    upper_inclusive::BOOLEAN AS upper_inclusive,
    is_null_band::BOOLEAN AS is_null_band,
    description::VARCHAR AS description

FROM read_csv_auto(
    'docs/references/gold_band_rules.csv',
    header = TRUE
)
;
