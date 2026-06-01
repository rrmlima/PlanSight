# Sprint 10 — Forecast Outlook

Data: 2026-06-01

## Objetivo
Adicionar uma visão de forecast ao PlanSight, usando o EVM atual do projeto para estimar:
- EAC (Estimate at Completion)
- ETC (Estimate to Complete)
- VAC (Variance at Completion)
- Completion %

A visão usa os mesmos filtros cruzados do dashboard:
- `date_window`
- `activity_code`

## Entrega
- Novo endpoint `GET /api/forecast`
- Novo bloco no frontend: **Forecast Outlook**
- Cards com:
  - EAC
  - ETC
  - VAC
  - Completion
- Resumo do snapshot atual com BAC, PV, EV e SPI
- Notas de forecast com leitura rápida do estado do projeto

## Regra de cálculo
O forecast foi calculado com base em SPI:
- `SPI = EV / PV`
- `EAC = BAC / (EV / PV)`
- `ETC = EAC - EV`
- `VAC = BAC - EAC`
- `Completion % = EV / EAC`

## Validação real
Foi validado localmente com upload via navegador de um XER mínimo contendo:
- `TASK`
- `PROJWBS`
- `TASKACTV`
- `TASKPRED`

### Endpoint validado
`GET /api/forecast?date_window=all&activity_code=all`

Resultado confirmado:
- `status: 200`
- `source: updated_xer`
- `current.bac: 390`
- `current.pv: 130`
- `current.ev: 105`
- `current.spi: 0.8077`
- `forecast.eac: 482.86`
- `forecast.etc: 377.86`
- `forecast.vac: -92.86`
- `summary.forecast_status: at_risk`
- `summary.forecast_completion_percent: 21.75`

### UI validada
O dashboard exibiu o novo bloco **Forecast Outlook** com os valores reais:
- EAC: `$483`
- ETC: `$378`
- VAC: `-$93`
- Completion: `22%`

## Testes
- `pytest /root/.hermes/plansight/tests/test_api.py -q`
- Resultado: `3 passed`

## Observações
- O forecast foi encaixado sem quebrar EVM, S-Curve, comparison, critical path e DCMA.
- A fórmula usa SPI do snapshot atual e está pronta para evoluir para cenários mais sofisticados depois.
