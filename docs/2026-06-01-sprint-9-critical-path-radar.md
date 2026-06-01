# Sprint 9 — Critical Path Radar

Data: 2026-06-01

## Objetivo
Adicionar uma leitura de *critical path* ao PlanSight, usando a rede de predecessoras em `TASKPRED` e o mesmo par de filtros do dashboard (`date_window` e `activity_code`).

## Entrega
- Novo endpoint `GET /api/critical-path`
- Novo painel no frontend: **Critical Path Radar**
- Reutilização do fluxo de filtros cruzados já existente no dashboard
- Destaque para:
  - duração total do caminho mais longo
  - lista ordenada de atividades críticas
  - atividades quase críticas com folga abaixo do threshold

## Regras de cálculo
- O caminho crítico é calculado a partir do grafo de precedência em `TASKPRED`.
- A duração por atividade é obtida em ordem de prioridade a partir dos campos:
  - `target_duration`
  - `remaining_duration`
  - `duration`
  - `orig_duration`
- Se não houver campo de duração, o backend usa um fallback de 1 dia por atividade.
- Atividades quase críticas são aquelas com `total_float_days <= 5` e que não pertencem ao caminho crítico.

## Contrato do endpoint
Resposta principal:
- `source`
- `filters`
- `summary`
- `critical_path_task_ids`
- `critical_path_task_names`
- `critical_path_tasks`
- `near_critical_task_ids`
- `near_critical_task_names`
- `near_critical_tasks`

## Validação real
Foi validado localmente com um XER mínimo carregado via navegador.

### Resultado do endpoint
`GET /api/critical-path?date_window=all&activity_code=all`

Retorno confirmado:
- `status: 200`
- `critical_path_task_ids: [1, 2, 3]`
- `critical_path_task_names: ["Design", "Build", "Test"]`
- `critical_path_duration_days: 19`
- `near_critical_task_ids: [4]`
- `near_critical_task_names: ["Packaging"]`
- `total_tasks: 4`

### Resultado visual
O dashboard carregou o novo bloco **Critical Path Radar** com:
- duração do caminho mais longo
- total de atividades
- lista do caminho crítico em ordem
- cartão de atividades quase críticas

## Testes
- `pytest /root/.hermes/plansight/tests/test_api.py -q`
- Resultado: `3 passed`

## Observações
- O Sprint 9 segue a linha do projeto: análise progressiva de cronograma sem sair do stack local.
- O painel foi encaixado no dashboard sem quebrar os componentes já existentes de EVM, S-Curve, comparação baseline/updated e schedule health.
