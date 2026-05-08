## Fontes de dados

A fonte de dados principal desse projeto vem o Kaggle [Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data) e as tabelas  `raw`
previstas no escopo inicial são:

- `application_train.csv`: dados de aplicações de crédito com variável *target*
- `application_test.csv`: dados de aplicações de crédito sem variável *target* - base de teste
- `bureau.csv`: histórico de crédito externo (em outras instituições)
- `bureau_balance.csv`: status mensal do histórico de crédito externo
- `previous_application.csv`: histórico de aplicações anteriores
- `POS_CASH_balance.csv`: histórico de empréstimos do tipo POS (parcelamento) e empréstimos em espécie
- `credit_card_balance.csv`: histórico de cartão de crédito
- `installments_payments.csv`: histórico de pagamentos parcelados

O *schema* esperado considerado para cada tabela pode ser encontrado
em [references](./references/HomeCredit_columns_description.csv), para que possa ser facilmente versionado caso as
tabelas sejam alteradas.
