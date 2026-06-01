# Pesquisa e decisão de naming — PlanSight

Data do registro: 2026-05-31

Este documento consolida a pesquisa feita durante a conversa para escolher o nome da ferramenta local de análise de arquivos Primavera P6 `.xer`.

## 1. Contexto do produto

O projeto nasceu como uma ferramenta local para Project Planners / Project Controls analisarem cronogramas exportados do Primavera P6 em formato `.xer`.

A ferramenta deve apoiar análises como:

- leitura/parsing de arquivos `.xer`;
- visualização de cronograma;
- dashboards de saúde do projeto;
- métricas EVM;
- checagem DCMA 14-point;
- análise de caminho crítico;
- comparação baseline vs. forecast;
- exportação de relatórios Excel;
- uso local, sem depender de cloud.

Restrições de implementação discutidas:

- sem admin rights;
- sem Docker;
- sem cloud obrigatória;
- backend Python puro;
- banco local com SQLite ou DataFrames;
- frontend HTML/JS/CSS com CDNs permitidos.

## 2. Nome anterior descartado

O nome inicial citado no projeto era **Vision**.

Ele foi descartado porque:

- é genérico demais;
- é muito usado em diversos mercados;
- não comunica diretamente `.xer`, planejamento, cronograma ou project controls;
- teria baixa diferenciação em busca/SEO.

## 3. Primeira rodada de nomes sugeridos

Foram consideradas alternativas em algumas famílias:

### Nomes técnicos ligados a XER / Primavera

- XERLens
- XERView
- XERInsight
- XERBoard
- XERDesk
- XERForge

### Nomes ligados a planejamento / cronograma

- PlanSight
- ScheduleIQ
- ScheduleForge
- BaselineIQ
- PathMetric
- CriticalSight
- FloatIQ
- ForecastPath

### Nomes ligados a project controls

- ControlPath
- ProjectPulse
- PlanControl
- ProjectControlsIQ
- MilestoneIQ
- EVMForge
- DCMACheck

## 4. Shortlist inicial

A shortlist priorizada para análise de presença foi:

1. PlanSight
2. XERLens
3. ScheduleIQ
4. ControlPath
5. ProjectPulse

A hipótese inicial era:

- **XERLens** seria forte como nome técnico por ser específico para `.xer`.
- **PlanSight** seria melhor como marca guarda-chuva por permitir expansão além do parser.

## 5. Método de pesquisa

A pesquisa foi feita como análise pragmática de presença online, não como parecer jurídico/marcário.

Foram considerados:

- buscas gerais pelo nome exato;
- variações com e sem espaço, quando aplicável;
- presença em Instagram;
- presença em Facebook;
- presença em LinkedIn;
- presença em Twitter/X;
- presença em Substack/newsletters;
- domínios `.com` e `.com.br`;
- quando relevante, domínios `.io`, `.co`, `.life` e páginas de produto;
- similaridade do produto encontrado com o nosso.

Critério de similaridade usado:

- **uso muito próximo** — mesmo tipo de produto, mesmo público, mesmo workflow ou mesmo input `.xer`/Primavera/P6;
- **uso moderado** — software/SaaS/analytics em área próxima, mas outro problema ou comprador;
- **uso distante** — termo usado em outro mercado ou em contexto técnico genérico;
- **ruído** — falsos positivos, posts soltos ou usos sem relação.

## 6. Resultado por nome

## 6.1 PlanSight

### Presença encontrada

Foi encontrada presença clara de **Plansight / PLANSIGHT** como empresa ativa.

Principais achados:

- `plansight.com` ativo.
- LinkedIn `linkedin.com/company/plansight`.
- Produto/serviço voltado a employee benefits RFP, brokers, carriers e renovações de benefícios.
- Uso de software/AI para automação de RFPs, extração de dados, comparação de propostas e apresentações para clientes.

Também apareceram resultados próximos como **Plainsight**, associado a computer vision/AI, mas não é o mesmo nome.

### Redes

- LinkedIn: ocupado por empresa ativa.
- Instagram/Facebook: mais ruído com “Plainsight” e “plain sight”; sem evidência forte de uso exato dominante.
- Twitter/X: sem evidência forte nos resultados encontrados.
- Substack: sem uso relevante exato encontrado.

### Domínios

- `plansight.com`: em uso ativo.
- `plansight.com.br`: sem resposta DNS/HTTP observada no teste. Necessário confirmar em registrador/Registro.br antes de qualquer conclusão de disponibilidade.

### Similaridade com nosso produto

Classificação: **uso distante a moderado**.

Não é concorrente direto de Primavera/P6/EVM/DCMA. Porém é software B2B com AI, análise de dados/documentos e automação.

### Veredito prático

**Nome parcialmente ocupado, mas utilizável como nome de trabalho.**

Riscos:

- `.com` indisponível;
- LinkedIn já ocupado;
- marca real de software B2B.

Pontos a favor:

- mercado diferente;
- colisão direta menor do que XERLens e ProjectPulse;
- nome mais amplo e bom para posicionamento de produto.

Recomendação da conversa: usar **PlanSight** como nome escolhido, sabendo que pode ser necessário usar modificadores em domínio/marca pública no futuro, como `PlanSight Controls`, `PlanSight Analytics`, `PlanSight Local` ou similar.

## 6.2 XERLens

### Presença encontrada

Foi encontrado `xerlens.com` ativo, com produto extremamente próximo ao nosso.

O site encontrado comunicava:

- visualização de plannings P6 sem licença Primavera;
- transformação de arquivos `.XER` em Gantt interativo;
- leitura de tabelas Primavera como `TASK`, `TASKPRED`, `PROJWBS`, `ACTVCODE`;
- importação `.XER`;
- comparação baseline vs. forecast;
- caminho crítico;
- DCMA 14 points;
- Monte Carlo;
- export PNG/PDF/HTML.

### Redes

- Instagram/Facebook/LinkedIn/Twitter/X/Substack: não foi encontrada presença social forte exata.
- Porém o domínio exato ativo com produto praticamente igual pesa mais do que ausência de redes sociais.

### Domínios

- `xerlens.com`: em uso ativo.
- `xerlens.com.br`: sem resposta DNS/HTTP observada no teste. Necessário confirmar formalmente.

### Similaridade com nosso produto

Classificação: **uso muito próximo**.

Motivos:

- mesmo tipo de arquivo: `.xer`;
- mesmo ecossistema: Primavera P6;
- mesmo tipo de análise: Gantt, DCMA, Monte Carlo;
- mesmo público provável: planners, schedulers, project controls.

### Veredito prático

**Descartar.**

Apesar de o nome ser excelente tecnicamente, a colisão é direta demais. Usar XERLens como marca pública poderia gerar confusão, dificuldade de SEO e aparência de cópia.

## 6.3 ScheduleIQ

### Presença encontrada

Foram encontradas várias presenças de **Schedule IQ / ScheduleIQ**.

Principais achados:

- `scheduleiq.io` ativo com produto de scheduling automation.
- LinkedIn `linkedin.com/company/schedule-iq`.
- Produto focado em inbound sales, booking de reuniões, roteamento de leads e integração com calendários.
- Histórico de outro ScheduleIQ como smart calendar/meeting scheduling, citado em publicações como Axios.
- Uso por Scheduling Solutions como analytics engine para manufatura, produção, schedule adherence, bottlenecks e integração com ERP/MES.
- Uso de “Schedule IQ” como feature de termostato Lennox S40.

### Redes

- LinkedIn: ocupado por Schedule IQ.
- Facebook/Instagram: presença parcial como feature/produto relacionado a scheduling.
- Twitter/X: sem perfil forte identificado nos resultados, mas há presença web suficiente.
- Substack: sem uso forte exato; muitos falsos positivos.

### Domínios

- `scheduleiq.com`: respondeu HTTP, aparentemente domínio registrado/página/lander.
- `scheduleiq.io`: em uso ativo.
- `scheduleiq.com.br`: sem resposta DNS/HTTP observada no teste.

### Similaridade com nosso produto

Classificação: **uso distante a moderado**.

A maioria dos usos está em agenda, calendário, reuniões, inbound sales, scheduling automation ou manufatura. Nosso produto é análise de cronograma de projeto Primavera P6.

### Veredito prático

**Evitar como marca principal.**

Não é tão perigoso quanto XERLens, mas é genérico, ocupado em software e pode confundir com agendamento de reuniões em vez de project controls.

## 6.4 ControlPath

### Presença encontrada

Não foi encontrada uma marca forte chamada **ControlPath** no nicho de Primavera/P6/project controls.

Apareceram muitos usos técnicos e genéricos:

- OpenSSH `ControlPath`;
- configuração SSH `ControlMaster` / `ControlPath`;
- Unity `InputControlPath`;
- bibliotecas de programação e termos de engenharia;
- resultados próximos como Control Point, ControlMap e Workflow Control.

### Redes

- Instagram/Facebook/LinkedIn/Substack: sem presença social forte exata como produto/empresa ControlPath.
- LinkedIn trouxe majoritariamente usos técnicos do termo ou cargos/descrições como controlpath/datapath.

### Domínios

- `controlpath.com`: DNS apontando para IP, mas sem site ativo carregável no teste HTTP/HTTPS.
- `controlpath.com.br`: sem resposta DNS/HTTP observada no teste.

### Similaridade com nosso produto

Classificação: **uso distante**.

O uso mais comum é técnico/infradev, não project controls.

### Veredito prático

**Nome relativamente limpo em concorrência direta, mas com ruído técnico.**

Pontos a favor:

- sem concorrente direto encontrado;
- comunica controle, caminho, caminho crítico e project controls.

Pontos contra:

- `controlpath.com` parece registrado;
- muito ruído de SEO com SSH/Unity/programação;
- pode parecer ferramenta de DevOps ou infraestrutura.

## 6.5 ProjectPulse

### Presença encontrada

Nome bastante ocupado.

Principais achados:

- `projectpulse.com` ativo com “Tools and Resources for project managers”.
- `projectpulse.life` ativo com ferramenta de project management.
- `projectpulse.co` ativo com produto de automação de status updates de projetos.
- LinkedIn `linkedin.com/company/projectpulseco`.
- `projectscheduling.com.au/projectpulse` com uso extremamente relevante: “ProjectPulse | Real-Time Schedule Intelligence”.
- Esse uso menciona schedule health metrics, forecasting, revision history, schedule evolution, Monte Carlo, ProjectPulsePro, Oracle Primavera P6, dashboards e stakeholders.
- Também apareceram GitHub `microsoft/project-pulse`, extensões VS Code, newsletters e páginas antigas/startups.

### Redes

- LinkedIn: ocupado por Project Pulse LLC e newsletter “The Project Pulse”.
- Facebook/Instagram: vários resultados de project management/project pulse/pulso.
- Twitter/X: referência antiga a `projectpulseio`.
- Substack: existe “The Project Pulse”.
- GitHub/marketplaces: vários usos técnicos.

### Domínios

- `projectpulse.com`: em uso ativo.
- `projectpulse.co`: em uso ativo.
- `projectpulse.life`: em uso ativo.
- `projectpulse.com.br`: sem resposta DNS/HTTP observada no teste.

### Similaridade com nosso produto

Classificação: **uso muito próximo**.

Especialmente por causa do uso ligado a schedule intelligence, Oracle Primavera P6, Monte Carlo e dashboards.

### Veredito prático

**Descartar como marca principal.**

É fácil de entender e comercialmente bom, mas justamente por isso está ocupado e possui colisões próximas demais.

## 7. Ranking final da pesquisa

### Mais limpos

1. **ControlPath**
   - Mais limpo no nicho direto.
   - Problemas: `.com` aparentemente registrado e ruído técnico.

2. **PlanSight**
   - Parcialmente ocupado, mas em mercado diferente.
   - Melhor como marca guarda-chuva do que nomes muito técnicos.

### Risco médio

3. **ScheduleIQ**
   - Ocupado em software e scheduling.
   - Não é concorrente direto de Primavera/P6, mas é genérico e saturado.

### Mais arriscados

4. **ProjectPulse**
   - Muito ocupado e com uso direto/semidireto em project management e schedule intelligence.

5. **XERLens**
   - O mais arriscado.
   - Produto ativo praticamente igual no recorte `.xer`/Primavera/Gantt/DCMA/Monte Carlo.

## 8. Decisão

Apesar de **ControlPath** parecer mais limpo em concorrência direta, o nome escolhido para o projeto foi:

# PlanSight

Justificativa:

- É mais amplo que XERLens e não prende o produto apenas ao parser `.xer`.
- Comunica análise, visibilidade e clareza sobre planos/cronogramas.
- Serve como marca guarda-chuva para módulos futuros.
- Tem menor colisão direta com Primavera P6/project controls do que XERLens e ProjectPulse.
- É mais amigável como nome de produto do que ControlPath, que soa mais técnico/devops.

## 9. Observações para uso futuro

Como `plansight.com` já está ocupado, se o projeto virar produto público será necessário pesquisar alternativas de domínio e identidade, por exemplo:

- `plansightcontrols.com`
- `plansightanalytics.com`
- `getplansight.com`
- `plansightlocal.com`
- `plansight.app`
- `plansight.com.br` se disponível no Registro.br

Também vale considerar um subtítulo para reduzir ambiguidade:

**PlanSight — Local P6/XER Schedule Intelligence**

ou em português:

**PlanSight — análise local de cronogramas Primavera P6**

## 10. Nota legal

Esta pesquisa é uma análise prática de presença online e risco de confusão. Não substitui busca formal de marca registrada no INPI, USPTO, EUIPO ou consulta jurídica especializada.
