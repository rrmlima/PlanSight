# 2026-05-31 — Sprint 3 frontend shell

## Assunto

Montagem da primeira casca visual do dashboard do **PlanSight** sem Node, sem NPM e sem build step, usando apenas um arquivo `index.html` com bibliotecas via CDN.

## Objetivo do sprint

Entregar a estrutura principal da UI com:

- `Vue 3` via CDN;
- `TailwindCSS` via CDN;
- layout dark moderno;
- sidebar esquerda com menu;
- área principal com barra de KPIs EVM;
- placeholders para S-Curve, WBS breakdown e resource histograms;
- chamada real ao endpoint `/api/evm-kpis` dentro do `mounted()` do Vue.

## Decisão técnica

A shell foi construída em um único arquivo:

- `index.html`

Motivos:

- respeita a restrição de não usar Node/NPM;
- permite abrir rapidamente em servidor estático local;
- simplifica iteração de UI no início do projeto;
- combina bem com o backend local já criado no Sprint 2.

## Implementação feita

## 1. `index.html` criado

Arquivo criado:

- `/root/.hermes/plansight/index.html`

O arquivo importa:

- `Vue 3` via `unpkg`
- `TailwindCSS` via CDN

Também inclui:

- configuração inline do Tailwind para tema escuro e cor de marca;
- CSS mínimo para `v-cloak` e fundo com gradientes sutis;
- app Vue criado com `createApp(...)` e montado em `#app`.

## 2. Layout geral

A tela foi estruturada em duas grandes áreas:

### Sidebar esquerda

Contém:

- marca PlanSight;
- subtítulo “Local Project Controls”;
- menu com:
  - Dashboard
  - Analysis
  - Profile
  - Settings
- cartão inferior de contexto do workspace.

### Área principal

Contém:

- top bar com título “Dashboard Overview”;
- indicação visual de status da API;
- indicação da fonte de dados (`updated_xer` / `original_xer`);
- faixa com cinco cartões de KPI:
  - BAC
  - PV
  - EV
  - SPI
  - CPI
- bloco grande com placeholder visual da S-Curve;
- bloco lateral com placeholders de donut para WBS breakdown;
- bloco lateral com barras placeholder para resource histograms.

## 3. Tema visual

A direção visual escolhida foi:

- dark theme;
- cards com transparência leve e blur;
- bordas suaves e arredondadas;
- acento em ciano/teal para identidade de produto;
- aparência de ferramenta analítica moderna, sem parecer template genérico claro.

## 4. Integração com a API

A conexão com a API local foi implementada no `mounted()` do Vue.

### Fluxo implementado

No carregamento da página:

1. o Vue chama `loadKpis()`;
2. `loadKpis()` faz `fetch('http://127.0.0.1:8000/api/evm-kpis')`;
3. se a resposta vier com sucesso, os dados são mapeados para o estado da UI;
4. se houver erro, a interface mostra uma mensagem amigável de fetch.

### Dados ligados à UI

Mapeamento feito:

- `BAC` ← `total_budget`
- `PV` ← `planned_value`
- `EV` ← `earned_value`
- `SPI` ← calculado no frontend como `EV / PV`
- `CPI` ← mantido como placeholder, pois ainda não existe AC exposto pela API

### Observação importante

O endpoint do Sprint 2 ainda não devolve `AC`, então o `CPI` não foi inventado artificialmente. A interface mostra um placeholder consistente em vez de um número enganoso.

## 5. Estados da interface

A shell já trata três estados simples:

- `loading`
- `ready`
- `error`

Esses estados afetam:

- o badge de status da API no topo;
- a mensagem de erro exibida acima dos KPIs, quando necessário.

## Validação executada

## Validação funcional

Para validar a UI com dados reais:

- o backend FastAPI foi iniciado na porta `8000`;
- um servidor estático local foi iniciado na porta `8020`;
- foi feito upload real de arquivos `.xer` de exemplo para popular a API;
- a interface foi carregada no navegador via `http://127.0.0.1:8020/index.html`.

## Resultado visual observado

A interface carregou corretamente com:

- sidebar visível;
- tema escuro consistente;
- KPI cards preenchidos com dados reais;
- status da API como `ready`;
- source como `updated_xer`;
- placeholders visíveis para:
  - S-Curve
  - donut charts
  - resource histograms

## Valores mostrados na UI durante a validação

- BAC: `$400`
- PV: `$280`
- EV: `$190`
- SPI: `0.68`
- CPI: `—`

## Arquivos criados/alterados no sprint

Criado:

- `index.html`

Nenhum arquivo de build, pacote ou dependência local foi adicionado.

## Estado final do sprint

O PlanSight agora já possui:

- backend local funcional;
- frontend shell funcional;
- ligação real entre frontend e endpoint de KPIs;
- base visual pronta para evoluir para gráficos reais, breakdowns reais e áreas de análise.

## Próximos passos naturais

- conectar upload de arquivos pela própria interface;
- substituir placeholders por gráficos reais;
- expor mais KPIs no backend, incluindo AC, SPI e CPI nativos;
- criar telas reais para Analysis, Profile e Settings;
- adicionar cards de tendência, variação e saúde do cronograma.
