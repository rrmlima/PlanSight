# Sprint 8 — Baseline vs Updated Comparison

Data: 2026-06-01

## Objetivo
Adicionar uma visão comparativa entre *baseline* e *updated* para o PlanSight, usando os dois arquivos `.xer` carregados no upload e reaproveitando os mesmos filtros do dashboard:

- `date_window`
- `activity_code`

## O que foi entregue

### Backend
Novo endpoint:

- `GET /api/baseline-compare`

Retorna:

- snapshot do baseline (`original`)
- snapshot do updated (`updated`)
- `delta` entre os dois conjuntos
- `task_changes` com:
  - `added`
  - `removed`
  - `modified`

A comparação é calculada com os mesmos filtros usados pelos demais endpoints do dashboard.

### Frontend
Foi adicionada uma seção visual nova no `index.html`:

- título: **Baseline vs Updated**
- cards de comparação para:
  - BAC
  - PV
  - EV
  - SPI
- resumo de tarefas:
  - added
  - removed
  - modified

O painel usa os mesmos filtros ativos do dashboard, então a visão comparativa fica sincronizada com a S-Curve, o EVM e o Schedule Health.

## Validação real

### Testes automatizados
Executado:

- `pytest /root/.hermes/plansight/tests/test_api.py -q`

Resultado:

- `3 passed in 1.71s`

### Validação no backend real
Com dois `.xer` mínimos enviados via `fetch` no navegador para `POST /upload`, os endpoints responderam com `200 OK`:

- `GET /api/baseline-compare?date_window=all&activity_code=all`
- `GET /api/evm-kpis?date_window=all&activity_code=con`
- `GET /api/schedule-health?date_window=all&activity_code=con`

### Validação visual no frontend
O dashboard carregou com dados reais e exibiu:

- KPI cards preenchidos
- S-Curve com dados carregados
- seção nova de comparação baseline vs updated
- seção de schedule health atualizada

## Observação
A comparação baseline vs updated foi implementada como Sprint 8 por ser o próximo incremento natural depois da filtragem cruzada do Sprint 7.
