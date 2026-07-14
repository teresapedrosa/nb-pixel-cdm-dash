# nb-cdm — Dashboard de métricas (Plane.so)

Dashboard estático de métricas de processo do time no projeto NBCDM
(Plane.so). Publicado via GitHub Pages, atualizado automaticamente toda
sexta-feira via N8N.

**Dashboard ao vivo:** https://teresapedrosa.github.io/nb-pixel-cdm-dash/

Decisões de arquitetura e regras de negócio (estados, story points,
retrabalho, cache incremental, etc.) estão em `ARCHITECTURE.md` — este
README é só setup e comandos do dia a dia. Se algo quebrar, ver
`GUIA-ATENCAO-MANUAL.md`.

---

## Setup

```bash
# 1. Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\activate         # Windows
source venv/bin/activate      # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env: PLANE_API_KEY, PROJECT_ID, PLANE_WORKSPACE_SLUG

# 4. Testar conexão com a API
python tests/test_connection.py
```

O teste de conexão valida autenticação, estados, cobertura do roster
(`src/team.py`) contra os assignees reais, e uso de labels de SP/tipo.

---

## Comandos do dia a dia

```bash
python -m src.data_layer          # sync incremental (issues/activities), salva data/issues.json
python -m src.metrics             # agrega métricas, salva data/metrics.json
python -m src.render              # gera docs/index.html (dashboard estático)
```

Ou tudo de uma vez (o que o N8N roda automaticamente toda sexta):

```bash
scripts\sync_and_publish.bat
```

Rebuild completo, ignorando o cache incremental de activities:

```bash
python -m src.data_layer --full
```

Publicar manualmente uma atualização fora do agendamento:

```bash
git add docs\index.html
git commit -m "sync manual"
git push
```

---

## Estrutura

```
nb-cdm/
├── src/
│   ├── plane_client.py     # Cliente base da API do Plane
│   ├── team.py             # Mapeamento do time (plane-id → nome/empresa/cargo/papel)
│   ├── labels.py           # Story points e tipo (bug/fix/feature) via labels
│   ├── time_utils.py       # Horas corridas, horas úteis, formatação dd/mm/aaaa
│   ├── cache.py            # Cache incremental de activities por updated_at
│   ├── data_layer.py       # Busca issues/activities, monta data/issues.json
│   ├── metrics.py          # Agrega dataset em data/metrics.json
│   └── render.py           # Gera docs/index.html (dashboard estático)
├── tests/
│   └── test_connection.py  # Validação da conexão e cobertura do roster
├── data/
│   ├── issues.json         # Dataset consolidado (uma linha por issue)
│   ├── issues_cache.json   # Cache incremental de activities
│   └── metrics.json        # Métricas agregadas — consumidas pelo render
├── docs/
│   └── index.html          # Dashboard estático — publicado via GitHub Pages
├── scripts/
│   └── sync_and_publish.bat  # Orquestra sync+métricas+render+push, chamado pelo N8N
├── logs/
│   └── ultimo_sync.log     # Log da última execução (ignorado pelo git)
├── outputs/                # Arquivos gerados (reports, exports)
├── .env.example
├── .gitignore
├── requirements.txt
├── ARCHITECTURE.md         # Decisões de arquitetura e regras de negócio
├── GUIA-ATENCAO-MANUAL.md  # O que fazer quando algo quebra
└── README.md
```

---

## Publicação e agendamento

Configurado e ativo — resumo rápido:

- **Repo:** github.com/teresapedrosa/nb-pixel-cdm-dash (público, necessário
  pro GitHub Pages gratuito)
- **Pages:** branch `main`, pasta `/docs`
- **N8N:** Schedule Trigger (sexta 08:00, cron `0 8 * * 5`) → Execute
  Command → `C:\nbcdm\scripts\sync_and_publish.bat`

Setup completo desses três itens (comandos de git, criação do repo,
configuração do node N8N) está documentado no histórico do projeto — se
precisar recriar do zero (ex. novo computador), pedir os comandos.

---

## Status

- [x] Passo 1 — Estrutura base, roster, validação de conexão
- [x] Passo 2 — Camada de dados
- [x] Passo 3 — Métricas + cache incremental
- [x] Passo 4 — Dashboard estático
- [x] Passo 5 — Agendamento via N8N + publicação GitHub Pages (ativo)
- [x] Passo 6 — Documentação (`ARCHITECTURE.md`, este README, guia manual)
