# Dashboard NB/Pixel — Métricas de Time via Plane.so

Dashboard interativo em Python, rodando em ambiente virtual, para acompanhamento
de métricas de processo do time via API do Plane.so. Reutiliza a arquitetura do
dashboard anterior, com escopo de time e regras de cálculo próprios deste projeto.

**Foco declarado:** mapear os integrantes do time, com prioridade de análise
sobre os integrantes da Pixel.

---

## Passo 1 — status

Conexão validada. Projeto confirmado como distinto do dashboard anterior.
Pontos levantados na validação e já endereçados no código:

- Estados do projeto: Backlog, Todo, In Progress, **Done, Finished**, Cancelled — Finished é o fim real do ciclo de vida do ticket.
- Assignees retornados pela API são UUIDs internos, não os slugs do time — resolução por e-mail implementada em `src/team.py` (`build_assignee_map`).
- Retrabalho por vínculo usa o campo `parent` (não existe endpoint de issue-relation na API pública do Plane).
- Story points vêm de labels (`SP 01`...`SP 08`, `SP 13+`), não do campo `estimate_point` — extração em `src/labels.py`.
- **Arthur Stein** (assignee fora do roster de 9 pessoas) foi excluído deliberadamente das métricas de dev.
- **Cobertura de SP**: 57/121 issues têm label de SP (distribuição: SP01=5, SP02=22, SP03=20, SP05=8, SP08=2). 64 issues ainda sem label de SP — provavelmente backlog não estimado ainda. Vale confirmar se isso é esperado ou se falta rotular tickets mais antigos.
- Nenhum ticket usa labels `fix`/`bug` ainda — a quebra por tipo vai mostrar 100% "feature" até que a equipe comece a rotular.

**Passo 1 encerrado.** Pronto para o Passo 2 (camada de dados).

---

## Time

| Nome | Empresa | Cargo | Papel na instrumentação | Plane ID |
|---|---|---|---|---|
| Fafis | Pixel | CEO | PO | `fabricio` |
| Tiago | NewByte | CTO - PO | PO | `tiago` |
| Felipe Chemin | NewByte | Dev - PI | Dev | `felipe.chemin` |
| Arthur | Pixel | Dev | Dev | `rosa.arthurh` |
| Marcos | Pixel | Dev | Dev | `marcosdamata2000` |
| Ritzel | NewByte | Dev - PI | Dev | `artur.ritzel` |
| GiPipolo | Pixel | Lead PM | PM | `giovanna` |
| Teresa | Pixel | PM | PM | `teresa` |
| Cauã Puppim | NewByte | PM - PI | PM | `caua.mendes` |

Mapeamento completo (e-mail, discord tag) em `src/team.py`. PMs e POs não entram
nas métricas de cycle time / story points por dev — apenas nas atribuições de
acompanhamento.

---

## Convenção de issues (Plane)

Prefixo dos tickets: `NBCDM-XX` (alterado de `NEWBY`; parsing de métricas não depende do prefixo).

**Estados reais deste projeto (validado via API, com atualização):** Backlog →
Todo → In Progress → **Done → Finished**, mais Cancelled.

- **Done**: Pixel entrega o ticket. Ainda sujeito a edits/fixes da NewByte.
- **Finished**: NewByte conferiu e aprovou, sem edits ou fixes pendentes. **Este é o ponto final da vida do ticket neste projeto** — não "Done".

O cronômetro de instrumentação começa quando o issue sai do Backlog (entra em
Todo). A partir daí, cada transição de estado gera um timestamp registrado
via endpoint de activities do Plane.

### Story points (via labels, não `estimate_point`)

Confirmado via API: este projeto usa **labels** para story points, não o
campo `estimate_point` do Work Item. Labels encontradas: `SP 01`, `SP 02`,
`SP 03`, `SP 05`, `SP 08`, `SP 13+`.

- `SP 13+` **não é um nível de story point regular** — é tratado como
  sinalizador automático de **issue grande demais**, e não entra na
  métrica de "tempo médio por nível de SP" por dev.
- `fix` e `bug` são labels separadas, usadas só para categorizar o tipo de
  ticket nos relatórios (bug / fix / feature) — não contam como retrabalho.

Lógica de extração em `src/labels.py`.

### Cycle time — regra de fallback

Vários tickets pulam o estado "In Progress" (vão direto de Todo para Done).
Nesses casos, cycle time (definido como primeiro In Progress → Done) fica
indefinido. Regra aplicada: **se não houver timestamp de In Progress, usar
Todo → Done como aproximação**, e marcar esses issues à parte como "sem
estágio intermediário registrado" nos relatórios — não misturar com o
cycle time "real" sem sinalização.

### Cobertura do time no Plane

Validação de membros do projeto encontrou 14 membros; 8 dos 9 nomes do
roster (`team.py`) foram resolvidos por e-mail. **Cauã Puppim não está
como membro deste projeto no Plane.** Se ele não recebe tickets atribuídos
diretamente (papel de PM-PI), isso não afeta as métricas — só impacta se
ele precisar aparecer como assignee em algum momento.

### Definição de retrabalho neste projeto

Sem QA/Verified, retrabalho é contado por dois critérios (qualquer um dos dois marca o issue):

1. **Reabertura por estado** — issue transicionou de Done **ou Finished** de volta para Todo ou In Progress.
2. **Vínculo com outro ticket** — existe outro issue com `parent` apontando para o ticket original (sub-item), tipicamente um bug/fix aberto referenciando o ticket-pai. **Não existe endpoint público de "issue relations" na API do Plane** — o campo `parent` já vem em cada issue retornado por `/issues/` e é a forma prática de detectar isso, sem chamada extra.

**Labels `fix` e `bug` NÃO entram nesse cálculo** — são apenas categorização do tipo de ticket (bug vs. feature vs. fix), usadas nos relatórios como quebra por tipo, não como sinal de retrabalho.

---

## Regras de cálculo desta versão

Diferenças em relação ao modelo anterior — aplicar em todo o dashboard:

| Regra | Definição |
|---|---|
| **Unidade de tempo** | Horas, não dias, em todas as métricas de tempo. |
| **Tempo estimado** | Convertido a partir de dias úteis × 8h (`WORK_HOURS_PER_DAY` no `.env`). |
| **Tempo real (lead/cycle time)** | Horas corridas entre timestamps de transição de estado. |
| **Tabela de issues** | Sem coluna de notas/descrição — apenas título do ticket. Descrição e descrição da resolução ficam no dataset para uso em detalhamento/exportação, não na tabela principal. |
| **KPIs de topo** | Apenas 3 cards: tickets concluídos, story points entregues, tickets em aberto. As demais métricas ficam nas seções abaixo do topo, não nos KPIs principais. |
| **Cadência de report** | Report mensal de junho primeiro. A partir daí, report semanal toda sexta-feira. |
| **Datas** | Formato dd/mm/aaaa em toda a interface e exports. |

---

## Métricas cobertas

**Topo (3 KPIs):**
- Tickets concluídos (chegaram a **Finished** no período — não Done)
- Story points entregues (no período)
- Tickets em aberto

**Processo:**
- Lead time (criação → **Finished**, em horas — ponto final real da vida do ticket)
- Cycle time (primeiro In Progress → **Done**, em horas — ciclo de entrega da Pixel)
- Tempo de homologação NewByte (Done → Finished, em horas — quanto tempo o ticket fica esperando aprovação/edits antes de fechar de vez)
- Throughput (issues que chegaram a Finished, por período)
- WIP (volume em In Progress)
- Retrabalho (issue reaberto de Done/Finished, e/ou issue vinculado ao ticket original — ver definição acima)
- Issues parados (em To Do/In Progress acima de `STUCK_THRESHOLD_HOURS`; incluir também issues presos em Done aguardando Finished há muito tempo)
- Issues grandes demais (sub-issues em excesso ou estimativa muito acima da média)
- Quebra por tipo de ticket (labels `bug` / `fix` / demais — categorização, não retrabalho)

**Por desenvolvedor:**
- Tempo médio de conclusão por nível de story point (SP 01, 02, 03, 05, 08), individual por dev
- Cycle time médio individual
- Volume entregue individual

**Detalhamento por issue (fora da tabela principal):**
- Descrição
- Descrição da resolução — preenchida apenas em casos de **retrabalho** (reabertura de Done ou ticket vinculado): registra qual foi a solução aplicada ao problema. Não se aplica a issues sem retrabalho.

---

## Setup

```bash
# 1. Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env: PLANE_API_KEY e PROJECT_ID (ver pendência acima)

# 4. Testar conexão com a API
python tests/test_connection.py

# 5. Sync incremental + métricas + dashboard
python -m src.data_layer          # busca issues/activities (cache incremental), salva data/issues.json
python -m src.metrics             # agrega métricas, salva data/metrics.json
python -m src.render              # gera docs/index.html (dashboard estático)
```

O teste de conexão também valida a cobertura do mapeamento de time
(`src/team.py`) contra os assignees reais encontrados nos issues, e
avisa se algum assignee não estiver mapeado.

`docs/index.html` é o dashboard publicável via GitHub Pages — arquivo único,
sem dependência de servidor. Rodar `python -m src.data_layer --full` força
um rebuild completo, ignorando o cache incremental (`data/issues_cache.json`).

---

## Publicação (GitHub Pages) e agendamento (N8N)

### 1. Primeiro push (rodar você mesma, uma vez só)

A pasta do projeto é sincronizada por OneDrive — `git init` e o primeiro push
são operações delicadas o suficiente pra rodar direto no seu terminal, não
por trás de mim. Na pasta do projeto, com o `venv` **desativado** (não precisa
dele pra isso):

```
git init
git branch -M main
git add .
git commit -m "Setup inicial do nb-cdm"
```

Criar o repositório no GitHub (via navegador, github.com/new): nome `nb-cdm`,
visibilidade **público** (necessário pro GitHub Pages gratuito — decisão já
confirmada). Depois:

```
git remote add origin https://github.com/<seu-usuario>/nb-cdm.git
git push -u origin main
```

Ativar o Pages: no repo, **Settings → Pages → Source: Deploy from a branch →
Branch: main, pasta: /docs → Save**. Em alguns minutos o link fica disponível
em `https://<seu-usuario>.github.io/nb-cdm/`.

**Confirma antes de commitar:** o `.gitignore` já exclui `.env`, `venv/`,
`data/*.json` e `logs/` — só código-fonte e `docs/index.html` vão pro repo
público. Vale um `git status` antes do primeiro commit pra conferir que
nenhum arquivo com credencial aparece na lista.

### 2. Script de sync (`scripts/sync_and_publish.bat`)

Orquestra o pipeline e publica — sem lógica de negócio, só chama os scripts
Python na ordem e faz o `git add`/`commit`/`push`:

```
scripts\sync_and_publish.bat
```

Roda `data_layer → metrics → render → git push`, e escreve o log da última
execução em `logs\ultimo_sync.log` (ignorado pelo git). Testar rodando esse
`.bat` manualmente uma vez, com o repo já publicado, antes de agendar no N8N.

### 3. Workflow no N8N

N8N só agenda — nenhuma lógica de cálculo entra no workflow, tudo já está no
`.bat`/Python:

1. Criar um novo workflow.
2. Nó **Schedule Trigger** — cadência semanal, sextas-feiras (regra do
   projeto era mensal em junho, depois semanal; como já estamos depois de
   junho, configurar direto semanal). Cron sugerido: `0 8 * * 5` (toda
   sexta, 08:00).
3. Nó **Execute Command**, conectado ao Schedule Trigger — comando apontando
   pro caminho completo do `.bat`:
   ```
   "C:\Users\teped\OneDrive\pixel_breeders\NewByte\cdm dashboard\scripts\sync_and_publish.bat"
   ```
4. Rodar o workflow manualmente uma vez (botão de teste no N8N) antes de
   ativar o agendamento, e conferir `logs\ultimo_sync.log` depois.
5. Ativar o workflow.

Se o `.bat` falhar silenciosamente do ponto de vista do N8N, o primeiro lugar
pra olhar é `logs\ultimo_sync.log` — todos os passos (sync, métricas, render,
push) escrevem lá, incluindo o motivo da falha.

---

## Estrutura

```
nb-cdm/
├── src/
│   ├── plane_client.py     # Cliente base da API do Plane
│   ├── team.py             # Mapeamento do time (plane-id → nome/empresa/cargo/papel)
│   ├── labels.py           # Story points e tipo (bug/fix/feature) via labels
│   ├── time_utils.py       # Horas corridas, horas úteis, formatação dd/mm/aaaa
│   ├── cache.py            # Passo 3 — cache incremental de activities por updated_at
│   ├── data_layer.py       # Passo 2/3 — busca issues/activities, monta data/issues.json
│   ├── metrics.py          # Passo 3 — agrega dataset em data/metrics.json
│   └── render.py           # Passo 4 — gera docs/index.html (dashboard estático)
├── tests/
│   └── test_connection.py  # Validação da conexão e cobertura do roster
├── data/
│   ├── issues.json         # Dataset consolidado (uma linha por issue)
│   ├── issues_cache.json   # Cache incremental de activities (não é o dataset final)
│   └── metrics.json        # Métricas agregadas — consumidas pelo Passo 4
├── docs/
│   └── index.html          # Dashboard estático — publicado via GitHub Pages
├── scripts/
│   └── sync_and_publish.bat  # Passo 5 — orquestra sync+métricas+render+push, chamado pelo N8N
├── logs/
│   └── ultimo_sync.log     # Log da última execução do sync_and_publish.bat (ignorado pelo git)
├── outputs/                # Arquivos gerados (reports, exports)
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Roadmap dos próximos passos

- [x] Passo 1 — Estrutura base, roster do time, validação de conexão
- [x] Passo 1.1 — Diagnóstico de estados, assignees, retrabalho, SP via labels
- [x] Passo 1.2 — Validação final: identidade de assignees, cobertura de SP, exclusão do Arthur Stein
- [x] Passo 2 — Camada de dados: buscar issues/activities, calcular timestamps em horas, aplicar regra de dias úteis para estimativas
- [x] Passo 3 — Métricas + cache incremental: lead time (→Finished), cycle time (→Done, com fallback), tempo de homologação (Done→Finished), throughput, WIP, retrabalho, issues parados, issues grandes (SP 13+), SP por dev. Cache por `updated_at` em `src/cache.py`, com flag `needs_retry` pra falhas de busca.
- [x] Passo 4 — Dashboard **estático** (HTML, publicado via GitHub Pages) — não Streamlit: 3 KPIs de topo + seções detalhadas, a partir de `data/metrics.json`
- [x] Passo 5 — Agendamento via N8N (Schedule Trigger → script) + publicação automática no GitHub Pages: `scripts/sync_and_publish.bat` pronto; falta você rodar o setup manual do git/Pages e configurar o workflow no N8N (ver seção "Publicação e agendamento" acima)
- [ ] Passo 6 — Exports (dd/mm/aaaa), `ARCHITECTURE.md`, README enxuto, guia de atenção manual
