# Fontes de Dados

A fonte principal do projeto é o dataset
[Home Credit Default Risk](https://www.kaggle.com/competitions/home-credit-default-risk/data). Os arquivos representam a
aplicação atual do cliente, histórico externo de crédito e relacionamento anterior com a instituição.

## Arquivos Esperados

| Arquivo | Papel analítico |
|---|---|
| `application_train.csv` | Aplicações com `TARGET`, base principal para entender inadimplência |
| `application_test.csv` | Aplicações sem `TARGET`, preservadas para manter compatibilidade com o dataset original |
| `bureau.csv` | Histórico externo de crédito, usado para sinais de exposição, dívida e bad debt |
| `bureau_balance.csv` | Evolução mensal do crédito externo, usada para DPD e severidade de atraso |
| `previous_application.csv` | Aplicações anteriores na instituição, usadas para recorrência, aprovação, recusa e valor solicitado |
| `POS_CASH_balance.csv` | Histórico mensal de contratos POS Cash, usado para atraso e estágio do contrato |
| `credit_card_balance.csv` | Uso de cartão, limite, saldo, saque e comportamento de pagamento mínimo |
| `installments_payments.csv` | Histórico de parcelas, atraso, pagamento parcial e valor em aberto |

## Referência de Schema

O dicionário original de colunas considerado no projeto está em
[references/HomeCredit_columns_description.csv](./references/HomeCredit_columns_description.csv).

Esse arquivo é usado pela Bronze como referência técnica de nomes e estrutura esperada. O valor analítico das variáveis
derivadas a partir dessas fontes está documentado em [Regras de negócio](./regras_de_negocio.md).
