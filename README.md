# PlanSight

PlanSight é o projeto local para análise de cronogramas Primavera P6 a partir de arquivos `.xer`.

## Objetivo do produto

Criar uma ferramenta local para Project Planners / Project Controls que leia arquivos Primavera P6 `.xer` e gere análises práticas, incluindo:

- parser local de `.xer`;
- dashboards de cronograma;
- métricas de EVM;
- checagens DCMA 14-point;
- relatórios em Excel;
- análises de baseline, forecast, caminho crítico, float e saúde do cronograma.

## Restrições iniciais

- Sem necessidade de admin rights.
- Sem Docker.
- Sem cloud obrigatória.
- Backend em Python puro, com possibilidade de FastAPI ou Flask.
- Banco local via SQLite ou DataFrames.
- Frontend HTML/JS/CSS, com CDNs permitidos.

## Nome escolhido

Nome de trabalho escolhido: **PlanSight**.

Racional curto:

- Comunica visão/clareza sobre plano e cronograma.
- É mais amplo que nomes presos apenas a `.xer`.
- Permite expansão futura para dashboards, EVM, DCMA, relatórios e outros formatos.
- Apesar de existir uso do nome em outro segmento de software B2B, a colisão direta com Primavera/P6/project controls parece menor do que em opções como XERLens e ProjectPulse.

## Estrutura da pasta

- `src/` — código-fonte inicial.
- `tests/` — testes futuros.
- `docs/` — documentação de produto e decisões.
- `research/` — pesquisas e registros de naming.

## Documentos importantes

- `research/naming-decision.md` — histórico completo da escolha do nome PlanSight.
