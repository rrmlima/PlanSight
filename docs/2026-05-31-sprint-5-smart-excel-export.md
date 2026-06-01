# Sprint 5 — Smart Excel Export

Data: 2026-05-31
Projeto: PlanSight

## Objetivo do sprint

Adicionar exportação Excel inteligente direto do backend Python, com foco no relatório:

- `Remaining Cost Export`
- múltiplas abas
- formatação nativa de Excel
- fórmulas `=SUBTOTAL()` para totais dinâmicos após filtros

## Abordagem

Segui TDD para o novo endpoint de exportação.

## RED — testes escritos primeiro

Arquivo:

- `tests/test_api.py`

Novos comportamentos cobertos:

1. `/api/export-excel` retorna `400` quando não há upload.
2. o módulo expõe a função Python geradora do arquivo:
   - `generate_remaining_cost_export(...)`
3. o endpoint retorna um `.xlsx` válido com:
   - abas `Raw Data` e `By WBS`
   - fórmulas `SUBTOTAL`
   - `autofilter`
   - formatação monetária
   - conditional formatting

### Resultado RED

Antes da implementação, os testes falharam com:

- `404 Not Found` em `/api/export-excel`
- ausência da função `generate_remaining_cost_export`

Comando executado:

```bash
pytest tests/test_api.py::test_export_excel_returns_400_before_upload tests/test_api.py::test_generate_remaining_cost_export_workbook_contains_tabs_formats_and_subtotals -q
```

## Implementações feitas

Arquivo alterado:

- `main.py`

## 1. Dependências instaladas

Foram instaladas no ambiente local:

- `xlsxwriter`
- `openpyxl`

Uso definido:

- `xlsxwriter` para geração do `.xlsx`
- `openpyxl` para validar a estrutura do workbook nos testes

## 2. Função Python de geração do relatório

Função criada:

- `generate_remaining_cost_export(tasks, wbs, source_label="api") -> bytes`

Ela:

- monta o dataframe detalhado de remaining cost por atividade;
- monta o summary agregado por WBS;
- gera o workbook em memória com `BytesIO`;
- retorna os bytes do `.xlsx` prontos para download.

### Helpers adicionados

- `_get_selected_project_dataset()`
- `_build_remaining_cost_dataframe(tasks, wbs)`
- `_build_wbs_remaining_summary(raw_df)`

## 3. Endpoint `/api/export-excel`

Endpoint criado:

- `GET /api/export-excel`

Comportamento:

- retorna `400` se não houver projeto carregado;
- usa `updated_xer` como fonte preferencial;
- gera o workbook em memória;
- devolve o arquivo com `StreamingResponse`.

Headers relevantes:

- `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `Content-Disposition: attachment; filename="remaining-cost-export.xlsx"`

## 4. Estrutura do Excel gerado

### Aba 1 — `Raw Data`

Contém colunas:

- `Task ID`
- `Task Name`
- `WBS ID`
- `WBS Name`
- `Budget`
- `Planned Value`
- `Earned Value`
- `Variance to Plan`
- `Remaining Cost`

### Fórmulas dinâmicas no topo

Foram inseridas fórmulas nativas do Excel:

- `=SUBTOTAL(9,E4:E5)` para budget visível
- `=SUBTOTAL(9,G4:G5)` para earned visível
- `=SUBTOTAL(9,I4:I5)` para remaining visível

### Fórmula dinâmica no rodapé

- `Filtered Total Remaining`
- `=SUBTOTAL(9,I4:I5)`

### Recursos nativos aplicados

- `AutoFilter`
- freeze panes
- colunas monetárias formatadas como `$#,##0.00`
- conditional formatting em `Variance to Plan`
  - verde para >= 0
  - vermelho para < 0

## 5. Aba 2 — `By WBS`

Contém agregação por WBS com colunas:

- `WBS ID`
- `WBS Name`
- `Budget`
- `Planned Value`
- `Earned Value`
- `Remaining Cost`

Também recebe:

- `SUBTOTAL()` no topo
- `AutoFilter`
- formatação monetária
- conditional formatting na coluna de remaining cost

## Regras de negócio implementadas

### Remaining Cost

```text
remaining_cost = budget - earned_value
```

### Variance to Plan

```text
variance_to_plan = earned_value - planned_value
```

Interpretação visual:

- positivo/zero → verde
- negativo → vermelho

## Validação automatizada

Comandos executados:

```bash
pytest tests/test_api.py -q
pytest tests -q
```

Resultado:

```text
6 passed
```

## Validação real do endpoint

Servidor FastAPI rodado localmente em `127.0.0.1:8000`.

### Upload real

```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F original_xer=@/tmp/plansight-original-s5.xer \
  -F updated_xer=@/tmp/plansight-updated-s5.xer
```

Resultado:

- upload aceito com `200 OK`

### Export real do Excel

```bash
curl http://127.0.0.1:8000/api/export-excel -o /tmp/remaining-cost-export.xlsx
```

O arquivo foi gerado com sucesso em:

- `/tmp/remaining-cost-export.xlsx`

### Leitura real do workbook gerado

O arquivo exportado foi reaberto com `openpyxl` para confirmar a estrutura.

Confirmações observadas:

- sheets: `['Raw Data', 'By WBS']`
- `Raw Data!A1 = Remaining Cost Export`
- `Raw Data!E2 = =SUBTOTAL(9,E4:E5)`
- `Raw Data!I6 = =SUBTOTAL(9,I4:I5)`
- `By WBS!C2 = =SUBTOTAL(9,C4:C5)`
- autofilter de `Raw Data`: `A3:I5`
- autofilter de `By WBS`: `A3:F5`

## Arquivos impactados

Criados/atualizados:

- `main.py`
- `tests/test_api.py`
- `docs/2026-05-31-sprint-5-smart-excel-export.md`

## Função principal entregue

A função Python solicitada pelo sprint está em:

- `main.py` → `generate_remaining_cost_export(...)`

Essa é a função central para geração do arquivo `.xlsx`.

## Próximo passo natural

Sprint 6 ideal:

- export Excel com gráficos embutidos
- aba de DCMA 14-point
- aba de summary executivo
- parâmetros de export por data slice / filtros / baseline vs updated
- estilos corporativos e branding do relatório
