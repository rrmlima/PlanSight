# 2026-05-31 — Sprint 2 API local setup

## Assunto

Implementação do backend local do **PlanSight** para servir dados do parser `.xer` à interface frontend via API HTTP.

## Objetivo do sprint

Entregar uma API local com:

- servidor FastAPI;
- endpoint `/upload` para receber um `.xer` original e um `.xer` atualizado opcional;
- integração do `XERParser` para processar os arquivos em memória;
- endpoint `/api/evm-kpis` para devolver KPIs básicos de projeto em JSON;
- CORS habilitado para o frontend HTML local consumir a API.

## Decisão técnica

Foi escolhido **FastAPI**.

Motivos:

- rápida para subir localmente;
- boa ergonomia para upload de arquivos;
- JSON nativo e claro para integração com frontend;
- simples de rodar com `uvicorn` em ambiente local.

## Estratégia de implementação

Segui uma abordagem de teste primeiro para o comportamento principal da API.

### Testes criados primeiro

Arquivo:

- `tests/test_api.py`

Cobertura inicial criada:

1. `/api/evm-kpis` deve retornar erro 400 quando ainda não existe upload.
2. `/upload` deve aceitar `original_xer` e `updated_xer`, processar ambos e armazenar os dados em memória.
3. `/api/evm-kpis` deve retornar os KPIs calculados a partir do dataset carregado.

### Resultado RED

O primeiro teste falhou porque `main.py` ainda não existia, o que confirmou que o teste estava realmente cobrindo comportamento ainda não implementado.

## Implementações feitas

## 1. `main.py` criado

Arquivo principal criado:

- `main.py`

Ele contém:

- criação do app FastAPI;
- middleware CORS com `allow_origins=["*"]`;
- armazenamento em memória em `app.state.project_data`;
- endpoint `POST /upload`;
- endpoint `GET /api/evm-kpis`;
- bloco `if __name__ == "__main__":` para rodar localmente com `uvicorn`.

## 2. Parser atualizado para suportar memória

Arquivo alterado:

- `src/xer_parser.py`

Novos métodos adicionados:

- `parse_text(text: str)`
- `parse_bytes(content: bytes)`
- `_build_tables_from_lines(lines)`

### Por que isso foi necessário

O parser original estava orientado a caminho de arquivo local.

Como o sprint pede upload via API e processamento em memória, foi necessário permitir que o `XERParser` consumisse bytes/texto já carregados do request, sem depender de salvar o arquivo de forma permanente em disco.

## 3. Endpoint `/upload`

Assinatura implementada:

- `original_xer: UploadFile = File(...)`
- `updated_xer: UploadFile | None = File(default=None)`

Comportamento:

- lê o conteúdo do upload;
- chama `XERParser.parse_bytes(...)`;
- armazena tabelas parseadas em memória;
- devolve resumo com tabelas encontradas e quantidade de tasks.

Formato de resposta implementado:

- mensagem de sucesso;
- snapshot do arquivo original;
- snapshot do arquivo atualizado, se existir.

## 4. Endpoint `/api/evm-kpis`

Comportamento:

- retorna `400` se não houver upload anterior;
- usa o `updated_xer` como fonte preferencial, se existir;
- caso contrário, usa o `original_xer`;
- calcula e devolve:
  - `total_budget`
  - `planned_value`
  - `earned_value`
  - `source`

## Regras de cálculo implementadas

Os cálculos foram implementados com heurística simples e prática para os campos mais prováveis do `TASK`.

### Total Budget

Busca primeiro uma das colunas:

- `target_cost`
- `at_completion_total_cost`
- `budget_at_completion`
- `total_cost`

Se nenhuma existir, usa zero.

### Planned Value

Busca primeiro:

- `planned_value`
- `bcws`

Se nenhuma existir, usa zero.

### Earned Value

Busca primeiro:

- `earned_value`
- `bcwp`

Se nenhuma existir, calcula via progresso físico:

- `budget * (phys_complete_pct / 100)`

Campos de progresso aceitos:

- `phys_complete_pct`
- `task_complete_pct`
- `complete_pct`
- `percent_complete`

## Arquivos criados/alterados no sprint

Criados:

- `main.py`
- `tests/test_api.py`

Alterados:

- `src/xer_parser.py`

## Validação executada

## Teste automatizado

Comando executado:

```bash
pytest tests/test_api.py -q
```

Resultado real:

```text
2 passed in 2.21s
```

## Validação real do servidor

O servidor foi iniciado localmente com Uvicorn na porta `8010`.

Uploads de exemplo foram enviados de verdade para o endpoint `/upload`, seguidos por leitura real do endpoint `/api/evm-kpis`.

### Resposta real do `/upload`

```json
{"message":"XER file(s) uploaded and parsed successfully.","original":{"tables":["PROJWBS","TASK","TASKACTV","TASKPRED"],"task_count":2},"updated":{"tables":["PROJWBS","TASK","TASKACTV","TASKPRED"],"task_count":2}}
```

### Resposta real do `/api/evm-kpis`

```json
{"total_budget":400.0,"planned_value":280.0,"earned_value":190.0,"source":"updated_xer"}
```

## Estado final do sprint

O PlanSight agora tem um backend local funcional capaz de:

- receber arquivos `.xer` via upload HTTP;
- processar esses arquivos em memória;
- armazenar os dados parseados localmente no processo;
- expor KPIs básicos em JSON para consumo por frontend local.

## Próximos passos naturais

- adicionar endpoint para inspeção de tabelas parseadas;
- expor diferenças entre original e atualizado;
- incluir KPIs adicionais como SV, CV, SPI e CPI;
- criar estrutura de sessão melhor caso o frontend passe a suportar múltiplos uploads em paralelo;
- conectar o frontend HTML a esses endpoints.
