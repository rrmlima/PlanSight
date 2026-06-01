# Sprint 4 — S-Curve e processamento de negócio

Data: 2026-05-31
Projeto: PlanSight

## Objetivo do sprint

Implementar a primeira camada de processamento temporal para o dashboard:

- cálculo de S-Curve com séries cumulativas de PV e EV;
- endpoint dedicado `/api/s-curve`;
- cálculo de pesos de WBS por budget;
- gráfico real no frontend;
- date slicer no cliente para filtrar a visualização sem novo roundtrip.

## Abordagem usada

Segui uma abordagem orientada a teste para o novo endpoint.

## RED — testes criados primeiro

Arquivo criado/recomposto:

- `tests/test_api.py`

Cobertura relevante deste sprint:

1. `/api/s-curve` retorna `400` quando não há upload carregado.
2. `/api/s-curve` retorna:
   - `source`
   - `data_date`
   - `dates`
   - `planned_value`
   - `earned_value`
   - `wbs_weights`
3. As séries retornadas são cumulativas e ordenadas por data.
4. Os pesos de WBS são agregados por budget e ordenados do maior para o menor.

### Resultado RED

Antes da implementação, os testes novos falharam com `404` no endpoint `/api/s-curve`, confirmando que o comportamento ainda não existia.

Comando executado:

```bash
pytest tests/test_api.py::test_s_curve_returns_400_before_upload tests/test_api.py::test_s_curve_returns_cumulative_arrays_and_wbs_weights -q
```

Falha observada:

- `404 Not Found` para `/api/s-curve`

## Implementações feitas no backend

Arquivo alterado:

- `main.py`

### 1. Novo endpoint `/api/s-curve`

O endpoint agora:

- retorna `400` se ainda não houver upload;
- prefere `updated_xer` quando disponível;
- retorna payload com séries da curva S e pesos de WBS.

Formato implementado:

```json
{
  "source": "updated_xer",
  "data_date": "2026-02-15",
  "dates": ["2026-01-20", "2026-01-31", "2026-02-15", "2026-02-28"],
  "planned_value": [0.0, 100.0, 100.0, 280.0],
  "earned_value": [90.0, 90.0, 190.0, 190.0],
  "wbs_weights": [
    {"wbs_id": 20, "label": "Mechanical", "weight": 62.5, "budget": 250.0},
    {"wbs_id": 10, "label": "Civil", "weight": 37.5, "budget": 150.0}
  ]
}
```

### 2. Heurísticas de cálculo temporal

Foram adicionados helpers para:

- localizar colunas por candidatos comuns (`_first_matching_column`);
- converter séries de datas por heurística (`_first_matching_datetime_series`);
- resolver o `data_date` a partir de colunas como:
  - `data_date`
  - `last_recalc_date`
  - `status_date`
  - ou fallback por datas reais/planejadas.

### 3. Geração da S-Curve

Função principal criada:

- `_build_event_curve(tasks, taskactv)`

Estratégia usada:

- usa `TASKACTV` quando a tabela estiver populada;
- faz fallback para `TASK` quando `TASKACTV` estiver vazia;
- usa colunas prováveis para PV:
  - `planned_value`
  - `bcws`
  - ou fallback para budget;
- usa colunas prováveis para EV:
  - `earned_value`
  - `bcwp`
  - ou fallback por `% complete` sobre budget;
- associa PV a datas planejadas de término;
- associa EV a datas reais de término ou ao `data_date` quando necessário;
- agrega por data com `pandas` e gera cumulativo ordenado.

### 4. Cálculo de pesos de WBS

Função criada:

- `_calculate_wbs_weights(tasks, wbs)`

Ela:

- agrega o budget por `wbs_id`;
- tenta resolver label em `PROJWBS`;
- calcula `%` relativo ao total;
- ordena da maior fatia para a menor.

## Implementações feitas no frontend

Arquivo alterado:

- `index.html`

### 1. Biblioteca de gráfico

Foi importado via CDN:

- `Chart.js 4`

### 2. Integração com a nova API

O frontend agora consome:

- `GET /api/evm-kpis`
- `GET /api/s-curve`

### 3. S-Curve real

A área antes placeholder virou um gráfico de linha real com:

- série `PV`
- série `EV`
- eixo X por data
- eixo Y formatado em moeda

### 4. Date slicer

Botões implementados:

- `Last 3M`
- `Last 6M`
- `All`

O filtro é client-side:

- usa os arrays já retornados pela API;
- recalcula o subconjunto visível no gráfico;
- evita nova chamada ao backend para cada clique.

### 5. WBS weights na interface

Os blocos laterais agora mostram dados reais:

- donuts/text rings com os maiores pacotes;
- lista completa com barras proporcionais;
- label e budget por WBS.

## Validação automatizada

Comandos executados:

```bash
pytest tests/test_api.py -q
pytest tests -q
```

Resultado:

```text
4 passed
```

## Validação real da API

Subi localmente:

- FastAPI em `127.0.0.1:8000`
- servidor estático em `127.0.0.1:8020`

Depois fiz upload real de arquivos `.xer` de amostra e consultei a API.

### Upload validado

```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F original_xer=@/tmp/plansight-original.xer \
  -F updated_xer=@/tmp/plansight-updated.xer
```

Resposta confirmada:

```json
{"message":"XER file(s) uploaded and parsed successfully.","original":{"tables":["PROJWBS","TASK","TASKACTV","TASKPRED"],"task_count":2},"updated":{"tables":["PROJWBS","TASK","TASKACTV","TASKPRED"],"task_count":2}}
```

### KPIs validados

```bash
curl http://127.0.0.1:8000/api/evm-kpis
```

Resposta:

```json
{"total_budget":400.0,"planned_value":280.0,"earned_value":190.0,"source":"updated_xer"}
```

### S-Curve validada

```bash
curl http://127.0.0.1:8000/api/s-curve
```

Resposta:

```json
{"source":"updated_xer","data_date":"2026-02-15","dates":["2026-01-20","2026-01-31","2026-02-15","2026-02-28"],"planned_value":[0.0,100.0,100.0,280.0],"earned_value":[90.0,90.0,190.0,190.0],"wbs_weights":[{"wbs_id":20,"label":"Mechanical","weight":62.5,"budget":250.0},{"wbs_id":10,"label":"Civil","weight":37.5,"budget":150.0}]}
```

## Validação visual no navegador

A interface foi aberta localmente em `http://127.0.0.1:8020/index.html`.

Foi confirmado visualmente que:

- o gráfico S-Curve renderizou com duas linhas (`PV` e `EV`);
- os botões `Last 3M`, `Last 6M` e `All` apareceram na UI;
- a tela mostrou `API status: ready`;
- a tela mostrou `Data source: updated_xer`;
- a tela mostrou `Data Date: 2026-02-15`;
- o bloco de WBS mostrou valores reais:
  - `Mechanical` com `$250` e ~`63%`
  - `Civil` com `$150` e ~`38%`

## Arquivos impactados

Criados/reestruturados:

- `tests/test_api.py`
- `docs/2026-05-31-sprint-4-s-curve-and-wbs.md`

Alterados:

- `main.py`
- `index.html`

## Decisões importantes do sprint

- Mantive o frontend no modelo single-file com CDN, sem Node/NPM.
- Mantive o backend local e em memória, sem persistência em banco.
- Usei heurística defensiva de colunas porque exports `.xer` podem variar bastante entre ambientes.
- O cálculo temporal foi preparado para priorizar `TASKACTV`, mas com fallback para `TASK` para não bloquear a evolução da UI.

## Próximo passo natural

Sprint 5 ideal:

- endpoint dedicado para breakdowns analíticos por WBS e disciplina;
- refino do algoritmo temporal para distribuir PV ao longo de períodos, e não apenas por marcos/eventos;
- preparação da camada DCMA 14-point;
- início dos datasets para histogramas reais de recursos.
