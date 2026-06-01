# Sprint 6 — Schedule Health (DCMA 14-Point parcial)

Data: 2026-05-31
Projeto: PlanSight

## Objetivo do sprint

Adicionar a primeira camada de auditoria técnica de cronograma baseada em regras DCMA, usando os dados `.xer` já parseados.

Escopo entregue neste sprint:

- checagens lógicas em `TASK` e `TASKPRED`;
- endpoint `GET /api/schedule-health`;
- implementação de 5 regras DCMA iniciais;
- exibição visual no frontend em formato de lista com barras de progresso.

## Regras implementadas

Foram implementadas estas 5 regras:

1. `Missing Logic`
   - atividades sem predecessor ou sem sucessor.
2. `Negative Float`
   - atividades com float negativo.
3. `High Float (>44 days)`
   - atividades com float maior que 44 dias.
4. `Invalid Dates`
   - atividades com datas reais após o `data_date`.
5. `Hard Constraints`
   - atividades com constraint rígida fora do conjunto soft aceito.

## Abordagem

Usei TDD também neste sprint.

## RED — testes escritos primeiro

Arquivo de testes atualizado:

- `tests/test_api.py`

Cobertura adicionada:

1. `/api/schedule-health` retorna `400` quando não há upload.
2. `/api/schedule-health` retorna:
   - `source`
   - `data_date`
   - `summary`
   - `rules`
3. cada regra retorna:
   - `rule_key`
   - `label`
   - `pass_percentage`
   - `offending_activity_ids`
   - `offending_count`
4. o cálculo de percentual médio geral é validado.

### Resultado RED

Antes da implementação, o novo teste falhou com `404 Not Found` para o endpoint `/api/schedule-health`.

Comando executado:

```bash
pytest tests/test_api.py::test_schedule_health_returns_400_before_upload tests/test_api.py::test_schedule_health_returns_dcma_rule_scores_and_offending_activity_ids -q
```

## Implementações feitas no backend

Arquivo alterado:

- `main.py`

### Helpers novos

Foram adicionadas funções auxiliares para a auditoria:

- `_normalize_activity_ids(...)`
- `_calculate_pass_percentage(...)`
- `_task_float_days(...)`
- `_build_schedule_health(tasks, taskpred, data_date)`

### Heurísticas aplicadas

#### Missing Logic

Usa `TASKPRED` para identificar:

- atividades que aparecem como sucessoras;
- atividades que aparecem como predecessoras.

Se a atividade não tiver predecessor ou não tiver sucessor, ela entra como ofensora.

#### Negative Float

Busca colunas prováveis de float:

- `total_float_days`
- `total_float_day_cnt`
- `total_float_hr_cnt`
- `total_float`

Se vier `total_float_hr_cnt`, a lógica converte horas para dias usando divisão por 8.

#### High Float

Usa o mesmo float normalizado e marca ofensores com valor `> 44` dias.

#### Invalid Dates

Compara `data_date` contra datas reais como:

- `act_start_date`
- `actual_start_date`
- `act_end_date`
- `actual_end_date`
- `completion_date`

Se a data real ficar depois do `data_date`, a atividade entra na lista.

#### Hard Constraints

Busca colunas como:

- `constraint_type`
- `cstr_type`
- `primary_constraint_type`

Considera soft constraints aceitas:

- `ASAP`
- `ALAP`
- `none`
- `SNET`
- `FNLT`
- `FNET`
- `SNLT`
- textos equivalentes `Start on or After` e `Finish on or Before`

Qualquer outro valor preenchido entra como hard constraint.

### Endpoint novo

Criado:

- `GET /api/schedule-health`

Payload retornado:

```json
{
  "source": "updated_xer",
  "data_date": "2026-02-15",
  "summary": {
    "total_activities": 4,
    "rule_count": 5,
    "average_pass_percentage": 65.0
  },
  "rules": [
    {
      "rule_key": "missing_logic",
      "label": "Missing Logic",
      "pass_percentage": 25.0,
      "offending_activity_ids": [1, 3, 4],
      "offending_count": 3
    }
  ]
}
```

## Implementações feitas no frontend

Arquivo alterado:

- `index.html`

### O que foi adicionado

- integração com `GET /api/schedule-health`
- novo bloco visual `Schedule Health Assessment`
- exibição do `overall pass`
- lista das 5 regras
- badge visual `PASS` ou `ATTENTION`
- barras de progresso por percentual de aprovação
- lista textual dos Activity IDs ofensores

### Comportamento visual

- verde quando o score é forte
- amarelo quando o score é intermediário
- vermelho quando o score é fraco

## Validação automatizada

Comandos executados:

```bash
pytest tests/test_api.py -q
pytest tests -q
```

Resultado real:

```text
8 passed
```

## Validação real da API

Subi localmente:

- FastAPI em `127.0.0.1:8000`
- servidor estático em `127.0.0.1:8020`

### Upload real usado na validação

Foi carregado um `.xer` de amostra com:

- 4 atividades
- 2 relações em `TASKPRED`
- um caso de float negativo
- um caso de high float
- um caso de invalid date
- um caso de hard constraint

### Resposta real do endpoint

```bash
curl http://127.0.0.1:8000/api/schedule-health
```

Resposta confirmada:

```json
{"source":"updated_xer","data_date":"2026-02-15","summary":{"total_activities":4,"rule_count":5,"average_pass_percentage":65.0},"rules":[{"rule_key":"missing_logic","label":"Missing Logic","pass_percentage":25.0,"offending_activity_ids":[1,3,4],"offending_count":3},{"rule_key":"negative_float","label":"Negative Float","pass_percentage":75.0,"offending_activity_ids":[3],"offending_count":1},{"rule_key":"high_float","label":"High Float (>44 days)","pass_percentage":75.0,"offending_activity_ids":[4],"offending_count":1},{"rule_key":"invalid_dates","label":"Invalid Dates","pass_percentage":75.0,"offending_activity_ids":[3],"offending_count":1},{"rule_key":"hard_constraints","label":"Hard Constraints","pass_percentage":75.0,"offending_activity_ids":[3],"offending_count":1}]}
```

## Validação visual no navegador

A UI foi aberta localmente em `http://127.0.0.1:8020/index.html`.

Foi confirmado que a tela mostrou corretamente:

- `Schedule Health Assessment`
- `Overall pass`
- `4 activities`
- regra `Missing Logic` com ofensores `1, 3, 4`
- regra `Negative Float` com ofensor `3`
- regra `High Float (>44 days)` com ofensor `4`
- regra `Invalid Dates` com ofensor `3`
- regra `Hard Constraints` com ofensor `3`

## Arquivos impactados

- `main.py`
- `index.html`
- `tests/test_api.py`
- `docs/2026-05-31-sprint-6-schedule-health-dcma.md`

## Observações técnicas

- a implementação é deliberadamente heurística porque os nomes de colunas do `.xer` podem variar entre ambientes;
- a regra de float já aceita hora ou dia e normaliza quando necessário;
- esse sprint entrega um DCMA parcial, não o conjunto completo de 14 checagens.

## Próximo passo natural

Sprint 7 ideal:

- expandir para mais regras DCMA
- distinguir milestones e exceções válidas de missing logic
- separar hard vs soft constraints com taxonomia mais rica
- adicionar drill-down por clique para abrir a lista detalhada de atividades
- permitir export da auditoria para Excel/PDF
