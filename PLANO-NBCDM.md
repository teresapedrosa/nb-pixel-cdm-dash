# Plano de ação — nb-cdm

Dashboard de métricas de time (projeto NBCDM, Plane.so), construído no Cowork
seguindo o modelo do V4 (`nb-pixel-dashboard`), com as regras de negócio
próprias deste projeto e as decisões de arquitetura consolidadas depois do V4.

---

## Decisão de arquitetura: estático, não interativo

O nb-cdm será um **dashboard estático (HTML exportado)**, publicado via
**GitHub Pages**, não um app Streamlit rodando local. Motivo: manter os dois
formatos em paralelo faz eles divergirem sozinhos com o tempo; escolher um só
evita isso. O N8N entra só como agendador (Schedule Trigger → script), nunca
como motor de cálculo.

Consequência prática: o Passo 4 do roadmap original (Streamlit) muda de forma
— vira geração de `docs/index.html` em vez de app servido. O código de
métricas (`metrics.py`) é o mesmo nos dois casos; muda só a camada de
apresentação.

Repo GitHub precisa ser **público** no plano free (Pages em repo privado exige
GitHub Pro, $4/mês) — a confirmar com você antes de criar o repo.

---

## Estado atual (herdado do V4, já reaproveitado)

Já existe em `cdm dashboard/`:

- `src/plane_client.py` — cliente da API do Plane
- `src/team.py` — roster de 9 pessoas (Pixel + NewByte), resolução de
  assignee por e-mail, Arthur Stein excluído deliberadamente
- `src/labels.py` — extração de story points via labels (`SP 01`...`SP 08`,
  `SP 13+`) e tipo (bug/fix/feature)
- `src/time_utils.py` — horas corridas, horas úteis, formatação dd/mm/aaaa
- `src/data_layer.py` — Passo 2, busca issues/activities
- `tests/test_connection.py` — validado: roster, estados, SP, retrabalho
  confirmados via API

Regras de negócio já fechadas (documentadas no `README.md` atual) — cycle
time, lead time, homologação, retrabalho, cobertura de SP, fallback Todo→Done
quando pula In Progress. Não é preciso redecidir nada disso, só implementar em
cima.

**Passo 3 (métricas/cache) e Passo 4 (apresentação) ainda não têm código** —
é o próximo trabalho real, não uma retomada de algo quebrado.

---

## Passos revisados

### Passo 3 — Camada de métricas
- `src/metrics.py`: agrega lead time, cycle time, homologação, throughput,
  WIP, retrabalho, issues parados, issues grandes (SP 13+), quebra por tipo,
  métricas por dev (SP, cycle time, volume)
- `src/cache.py`: cache incremental por `updated_at` — só rebusca o que
  mudou desde o último sync; pula de cara itens em estado sem histórico
  relevante (backlog puro)
- Cache guarda um flag `incomplete`/`needs_retry` separado de "vazio de
  verdade" — se uma busca falhar (429, timeout), isso não pode virar "sem
  dado" congelado pra sempre, porque nada mais vai tocar o `updated_at` pra
  forçar nova tentativa
- Se buscas rodarem em threads paralelas, usar throttle compartilhado entre
  workers pra não estourar rate limit da API

### Passo 4 — Geração do dashboard estático
- Script gera `docs/index.html` a partir de `data/cache.json`
- 3 KPIs de topo (concluídos, SP entregues, em aberto) + seções abaixo:
  processo, por desenvolvedor, quebra por tipo
- Tabela principal só com título do ticket (sem descrição) — descrição e
  descrição da resolução ficam disponíveis pra detalhamento/export, fora da
  tabela
- Datas em dd/mm/aaaa em toda a interface

### Passo 5 — Agendamento (N8N)
- N8N = Schedule Trigger → Execute Command chamando `.bat`/script local, sem
  lógica de negócio no workflow
- Script faz: sync incremental → recalcula métricas → gera `docs/index.html`
  → `git add`/`commit`/`push` (publica no GitHub Pages)
- Cadência: mensal (junho) primeiro, depois semanal (toda sexta)
- Checagem no início do script: `if not exist .venv\Scripts\python.exe echo
  AVISO...` — `.venv` pode sumir por limpeza/sync do OneDrive e quebrar tudo
  silenciosamente
- No `.bat`: `cd /d "%~dp0"` no topo, não usar `-C "%~dp0"` em comando git
  (barra invertida final quebra parsing de aspas no Windows)

### Passo 6 — Exports e documentação final
- Exports em dd/mm/aaaa; planilha em locale UK se for necessária
- `ARCHITECTURE.md`: decisões de arquitetura deste projeto (fonte única,
  sem diário de "resumo do dia X")
- `README.md`: enxuto, só setup e comandos do dia a dia
- Guia separado "o que precisa de atenção manual", pensado pra quem não lê
  código (ex.: o que fazer se o sync falhar, como forçar retry, como trocar
  a API key)

---

## Como vamos trabalhar

A pasta do projeto é sincronizada por OneDrive — meu acesso via terminal pode
ficar instável pra operações delicadas (`git init`, primeiro push, etc). Para
essas etapas, te passo o comando pronto pra colar no seu terminal, em vez de
tentar rodar por trás.

---

## Pendências / decisões em aberto

- Repo confirmado como **público** — necessário pro GitHub Pages gratuito.
- N8N já roda no seu ambiente — falta só criar o workflow (Schedule Trigger
  + Execute Command apontando pro `scripts/sync_and_publish.bat`).
- **Falta rodar manualmente**: `git init` + primeiro push + ativar Pages nas
  configurações do repo (comandos prontos no README, seção "Publicação e
  agendamento") — não executo isso por trás por ser pasta OneDrive.
- `Cauã Puppim` não aparece como membro do projeto no Plane — só afeta
  métricas se ele passar a receber tickets diretamente.

---

## Roadmap

- [x] Passo 1 — Estrutura base, roster, validação de conexão
- [x] Passo 2 — Camada de dados (issues/activities, horas, dias úteis)
- [x] Passo 3 — Métricas + cache incremental com flag de retry
- [x] Passo 4 — Geração de dashboard estático (`docs/index.html`) — testado ponta a ponta com dados reais, números validados por você
- [x] Passo 5 — Código pronto (`scripts/sync_and_publish.bat` + `.gitignore` + instruções no README); falta você rodar o setup manual do git/GitHub Pages e criar o workflow no N8N
- [ ] Passo 6 — Exports, `ARCHITECTURE.md`, README enxuto, guia manual
