# Sprint 11 — AC/CPI Cost Performance

Data: 2026-06-01

## Objetivo
Transformar o card de custo do dashboard em um painel real, expondo:
- `AC` — Actual Cost
- `CPI` — Cost Performance Index

O bloco continua usando os mesmos filtros do dashboard:
- `date_window`
- `activity_code`

## Entrega
- `GET /api/evm-kpis` agora devolve:
  - `actual_cost`
  - `cpi`
- O card do frontend deixa de ser placeholder e passa a exibir:
  - `AC`
  - `CPI`
- O estado inicial do Vue foi ajustado para suportar o novo KPI sem quebrar o primeiro render.

## Regra de cálculo
- `AC` é calculado somando colunas de custo reais quando presentes no TASK:
  - `actual_cost`
  - `act_cost`
  - `act_reg_cost`
  - `act_labor_cost`
  - `act_mat_cost`
  - `act_equip_cost`
  - `actual_expense`
- `CPI = EV / AC`

Quando não houver custo real, o sistema responde com `AC = 0` e `CPI = null`.

## Validação real
Foi validado localmente com upload via navegador de um XER mínimo contendo:
- `TASK`
- `PROJWBS`
- `TASKACTV`
- `TASKPRED`
- coluna `actual_cost` em `TASK`

### Endpoint validado
`GET /api/evm-kpis?date_window=all&activity_code=all`

Resultado confirmado:
- `status: 200`
- `source: updated_xer`
- `total_budget: 390`
- `planned_value: 130`
- `earned_value: 105`
- `actual_cost: 107`
- `spi: 0.8077`
- `cpi: 0.9813`

### UI validada
O dashboard exibiu os cards reais:
- AC: `$107`
- CPI: `0.98`

## Testes
- `pytest -q`
- Resultado: `2 passed`

## Observações
- O dashboard agora não mostra mais placeholder de custo.
- A fórmula foi pensada para aceitar diferentes nomes de colunas de custo, reduzindo a chance de quebrar em XERs reais com variação de schema.
