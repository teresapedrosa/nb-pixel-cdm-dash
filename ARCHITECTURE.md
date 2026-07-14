# Arquitetura — nb-cdm

Fonte única das decisões de arquitetura e regras de negócio deste projeto.
Não é um diário de "resumo do dia X" — quando uma decisão muda, este arquivo
é editado no lugar, não duplicado. Setup e comandos do dia a dia ficam no
`README.md`; o que fazer quando algo quebra fica no `GUIA-ATENCAO-MANUAL.md`.

---

## Objetivo

Dashboard de métricas de processo do time no projeto NBCDM (Plane.so), com
foco declarado em mapear os integrantes do time, priorizando a Pixel.
Construído a partir do modelo do dashboard anterior (V4), com regras de
negócio e decisões de arquitetura próprias deste projeto.

---

## Decisão: dashboard estático, não interativo

O nb-cdm é um **dashboard estático (HTML exportado)**, publicado via
**GitHub Pages** — não um app Streamlit rodando local. Motivo: manter os
dois formatos em paralelo faz eles divergirem sozinhos com o tempo; escolher
um só evita isso. `src/render.py` gera `docs/index.html`, um arquivo único,
sem dependência de servidor.

Consequência: `requirements.txt` não inclui `streamlit` nem `pandas` —
nenhum dos dois é usado pelo código atual (JSON + `statistics` da stdlib
bastam para as agregações).

## Decisão: N8N só agenda, nunca calcula

N8N entra só como agendador (Schedule Trigger → Execute Command chamando
`scripts/sync_and_publish.bat`), nunca como motor de cálculo. Lógica de
negócio em nó de workflow é difícil de testar e versionar — toda a lógica
fica em `src/*.py`, testável isoladamente.

## Decisão: GitHub Pages, repo público

Repo GitHub (`nb-pixel-cdm-dash`) é **público** — necessário pro GitHub
Pages funcionar no plano free (Pages em repo privado exige GitHub Pro,
$4/mês). Confirmado com a Teresa antes da criação do repo. Consequência:
código-fonte e o HTML gerado ficam visíveis publicamente — dados sensíveis
(`.env`, credenciais) nunca entram no repo (ver `.gitignore`).

---

## Cache incremental (`src/cache.py`)

O endpoint de activities do Plane (`get_issue_activities`) é uma chamada
por issue — caro em projetos grandes. O cache incremental evita rebuscar
activities de issues cujo `updated_at` não mudou desde o último sync.

Regra importante: se uma busca falhar (rate limit, timeout, erro de rede),
o issue é marcado com status `needs_retry` — nunca vira um registro vazio
silencioso. Um cache incremental por `updated_at` só refaz a busca quando o
valor muda; se uma falha virasse "vazio" sem sinalização, esse vazio
ficaria congelado pra sempre, porque nada mais tocaria o `updated_at` do
issue pra forçar nova tentativa. `needs_retry` ignora o `updated_at` e
sempre tenta de novo no próximo sync.

Issues em **Backlog** pulam a busca de activities inteiramente (não têm
cronômetro relevante) e não entram no cache — se saírem do Backlog depois,
são buscados do zero.

Se o sync passar a rodar em threads paralelas no futuro, trocar o
`time.sleep` sequencial em `cache.throttle()` por um throttle/semaphore
compartilhado entre workers — múltiplas threads sem throttle comum é o
jeito clássico de estourar rate limit mesmo com delay configurado em cada
uma isoladamente.

---

## Regras de negócio (Plane)

### Estados e ciclo de vida

Estados reais do projeto: **Backlog → Todo → In Progress → Done → Finished
→ (Cancelled)**. Sem QA/Verified.

- **Done**: Pixel entrega o ticket. Ainda sujeito a edits/fixes da NewByte.
- **Finished**: NewByte conferiu e aprovou, sem edits ou fixes pendentes.
  **Este é o ponto final da vida do ticket neste projeto** — não "Done".

O cronômetro de instrumentação começa quando o issue sai do Backlog (entra
em Todo). Cada transição de estado gera um timestamp via endpoint de
activities do Plane.

### Story points via labels (não `estimate_point`)

Este projeto usa **labels** para story points, não o campo `estimate_point`
do Work Item. Labels: `SP 01`, `SP 02`, `SP 03`, `SP 05`, `SP 08`, `SP 13+`.

- `SP 13+` não é um nível regular de SP — é o sinalizador automático de
  "issue grande demais" (`oversized`), fora da métrica de tempo médio por
  nível de SP.
- `fix` e `bug` são labels de categorização (bug / fix / feature nos
  relatórios) — **não contam como retrabalho**.

Lógica em `src/labels.py`.

**Truque de dados que pode se repetir:** se o campo "óbvio" da ferramenta
(aqui, `estimate_point`) vem vazio, olhar os labels antes de desistir —
times às vezes codificam metadado (SP, prioridade, etc.) como label em vez
de usar o campo nativo.

### Cycle time — regra de fallback

Muitos tickets pulam o estado "In Progress" (vão direto de Todo para Done).
Cycle time é definido como primeiro **In Progress → Done**; quando não há
timestamp de In Progress, usa-se **Todo → Done** como aproximação, marcado
à parte (`cycle_time_fallback: true`) — nunca misturado ao cycle time
"real" sem sinalização.

### Retrabalho

Sem QA/Verified, retrabalho é contado por dois critérios (qualquer um dos
dois marca o issue):

1. **Reabertura por estado** — issue transicionou de Done ou Finished de
   volta para Todo ou In Progress.
2. **Vínculo com outro ticket** — existe outro issue com `parent` apontando
   pro ticket original (sub-item, tipicamente bug/fix referenciando o
   ticket-pai). Não existe endpoint público de "issue relations" na API do
   Plane — o campo `parent` já vem em cada issue de `/issues/`, sem chamada
   extra.

Labels `fix`/`bug` **não** entram nesse cálculo — são só categorização.

### Assignees e roster do time

Assignees vêm como UUID interno da API — resolvidos por e-mail contra o
roster em `src/team.py` (`build_assignee_map`). **Arthur Stein** aparece
como assignee em tickets deste projeto mas foi excluído deliberadamente do
roster — fica fora das métricas de dev, mas ainda conta nas métricas
agregadas do projeto.

| Nome | Empresa | Cargo | Papel | Plane ID |
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

PMs e POs não entram nas métricas de cycle time/story points por dev —
só nas atribuições de acompanhamento. **Cauã Puppim não aparece como
membro do projeto no Plane** — só afeta métricas se ele passar a receber
tickets atribuídos diretamente.

---

## Regras de cálculo e apresentação

| Regra | Definição |
|---|---|
| Unidade de tempo | Horas, não dias, em todas as métricas. |
| Tempo estimado | Dias úteis × 8h (`WORK_HOURS_PER_DAY` no `.env`). |
| Tempo real (lead/cycle time) | Horas corridas entre timestamps de transição de estado. |
| Tabela de issues | Só título — sem descrição/notas. Descrição e resolução ficam no dataset completo, fora da tabela principal. |
| KPIs de topo | Só 3 cards: tickets concluídos (Finished), SP entregues, tickets em aberto. |
| Cadência de report | Mensal (junho) → depois semanal (sextas), via N8N. |
| Datas | dd/mm/aaaa em toda a interface e exports. |

**Lead time** = criação → Finished (ponto final real do ticket).
**Cycle time** = primeiro In Progress → Done (ciclo de entrega da Pixel),
com fallback Todo → Done.
**Homologação NewByte** = Done → Finished (tempo esperando aprovação).

---

## Gotchas de Windows (evitar de novo)

- **`%~dp0` sempre termina em barra invertida.** `-C "%~dp0"` em comando
  git quebra o parser de aspas — usar `cd /d "%~dp0"` no topo do script em
  vez disso (feito em `scripts/sync_and_publish.bat`).
- **`.venv`/`venv` pode sumir sozinho** (limpeza, sync do OneDrive) e
  quebrar o pipeline silenciosamente. `sync_and_publish.bat` checa
  `venv\Scripts\python.exe` antes de tudo e aborta com aviso claro se não
  encontrar.
- **Node Execute Command do N8N não lida bem com espaço em caminho no
  Windows**, mesmo com aspas — corta o comando no primeiro espaço. A pasta
  deste projeto (`cdm dashboard`) tem espaço no nome. Correção: junction
  sem espaço apontando pra pasta real:
  ```
  mklink /J C:\nbcdm "C:\Users\teped\OneDrive\pixel_breeders\NewByte\cdm dashboard"
  ```
  O campo Command no node N8N usa `C:\nbcdm\scripts\sync_and_publish.bat`
  (sem aspas) — os arquivos continuam na pasta real, a junction é só um
  caminho alternativo sem espaço.

---

## Estrutura de arquivos

Ver `README.md` — a árvore de pastas com o papel de cada arquivo é mantida
lá (referência prática), não duplicada aqui.

---

## Histórico de decisões revertidas ou re-avaliadas

- Nenhuma até o momento. Quando uma decisão de arquitetura for revertida,
  registrar aqui o motivo em vez de apagar a decisão anterior sem
  explicação.
