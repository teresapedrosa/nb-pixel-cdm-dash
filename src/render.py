"""
Passo 4 — Dashboard estático.

Lê data/metrics.json (agregado, Passo 3) e data/issues.json (dataset por
issue, Passo 2/3) e gera um único arquivo HTML autocontido em docs/index.html
— sem servidor, sem build step. Publicado via GitHub Pages (repo público no
plano free).

Decisão de arquitetura: estático, não Streamlit — evita manter dois formatos
de dashboard que divergem sozinhos com o tempo (ver PLANO-NBCDM.md).

Uso:
    python -m src.render              # lê data/*.json, gera docs/index.html
"""

import os
import json
import html as html_escape
from datetime import datetime

from . import time_utils as tu

METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metrics.json")
ISSUES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "issues.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")

ESTADO_ORDEM = ["In Progress", "Todo", "Backlog", "Done", "Finished", "Cancelled"]


def _e(value) -> str:
    """Escapa texto pra uso seguro dentro de HTML."""
    if value is None:
        return ""
    return html_escape.escape(str(value))


def _fmt_horas(v) -> str:
    return f"{v:g}h" if v is not None else "—"


def _fmt_pct(v) -> str:
    return f"{v}%" if v is not None else "—"


def _badge_estado(estado: str) -> str:
    classe = {
        "Backlog": "estado-backlog",
        "Todo": "estado-todo",
        "In Progress": "estado-in-progress",
        "Done": "estado-done",
        "Finished": "estado-finished",
        "Cancelled": "estado-cancelled",
    }.get(estado, "estado-outro")
    return f'<span class="badge {classe}">{_e(estado)}</span>'


def _badge_tipo(tipo: str) -> str:
    classe = {"bug": "tipo-bug", "fix": "tipo-fix", "feature": "tipo-feature"}.get(tipo, "tipo-feature")
    return f'<span class="badge {classe}">{_e(tipo)}</span>'


def _kpi_cards(kpis: dict) -> str:
    cards = [
        ("Tickets concluídos", kpis.get("tickets_concluidos"), "chegaram a Finished"),
        ("Story points entregues", kpis.get("story_points_entregues"), "issues em Finished, com SP"),
        ("Tickets em aberto", kpis.get("tickets_em_aberto"), "fora de Finished/Cancelled"),
    ]
    html_cards = "".join(
        f"""
        <div class="kpi-card">
            <div class="kpi-valor">{_e(valor if valor is not None else "—")}</div>
            <div class="kpi-label">{_e(label)}</div>
            <div class="kpi-sub">{_e(sub)}</div>
        </div>"""
        for label, valor, sub in cards
    )
    return f'<div class="kpi-grid">{html_cards}</div>'


def _metric_card(label: str, valor: str, sub: str = "") -> str:
    sub_html = f'<div class="metric-sub">{_e(sub)}</div>' if sub else ""
    return f"""
        <div class="metric-card">
            <div class="metric-valor">{_e(valor)}</div>
            <div class="metric-label">{_e(label)}</div>
            {sub_html}
        </div>"""


def _secao_processo(p: dict) -> str:
    lt, ct, hm = p["lead_time_horas"], p["cycle_time_horas"], p["homologacao_horas"]
    rt = p["retrabalho"]

    cards = "".join([
        _metric_card("Lead time médio", _fmt_horas(lt["media"]), f"criação → Finished · n={lt['n']}"),
        _metric_card("Cycle time médio", _fmt_horas(ct["media"]), f"In Progress → Done · n={ct['n']}"),
        _metric_card(
            "  ↳ com fallback (Todo→Done)",
            _fmt_horas(ct["com_fallback_todo_done"]["media"]),
            f"pulou In Progress · n={ct['com_fallback_todo_done']['n']}",
        ),
        _metric_card("Homologação NewByte", _fmt_horas(hm["media"]), f"Done → Finished · n={hm['n']}"),
        _metric_card("WIP", p["wip"], "issues em In Progress"),
        _metric_card("Retrabalho", f"{rt['total']} ({_fmt_pct(rt['percentual'])})",
                     f"{rt['por_reabertura']} por reabertura · {rt['por_vinculo']} por vínculo"),
        _metric_card("Issues parados", p["parados"], "acima do limiar configurado"),
        _metric_card("Oversized (SP 13+)", p["oversized_sp13_mais"], "candidatos a quebrar em sub-tickets"),
    ])

    throughput = p.get("throughput_por_mes", {})
    max_t = max(throughput.values()) if throughput else 1
    throughput_html = "".join(
        f"""
        <div class="bar-row">
            <div class="bar-label">{_e(mes)}</div>
            <div class="bar-track"><div class="bar-fill" style="width:{round(100 * qtd / max_t)}%"></div></div>
            <div class="bar-valor">{qtd}</div>
        </div>"""
        for mes, qtd in throughput.items()
    ) or '<p class="vazio">Sem dados de throughput ainda.</p>'

    tipo = p.get("quebra_por_tipo", {})
    tipo_html = "".join(
        f'<div class="tipo-item">{_badge_tipo(t)} <span>{qtd}</span></div>' for t, qtd in tipo.items()
    )

    return f"""
    <section>
        <h2>Processo</h2>
        <div class="metric-grid">{cards}</div>
        <h3>Throughput por mês (issues que chegaram a Finished)</h3>
        <div class="bar-chart">{throughput_html}</div>
        <h3>Quebra por tipo</h3>
        <div class="tipo-grid">{tipo_html}</div>
    </section>"""


def _secao_por_dev(por_dev: dict) -> str:
    linhas = []
    for nome, m in sorted(por_dev.items(), key=lambda kv: -(kv[1]["volume_entregue"] or 0)):
        sp_breakdown = ", ".join(
            f"SP{sp}: {_fmt_horas(v)}" for sp, v in m["tempo_medio_horas_por_story_point"].items()
        ) or "—"
        linhas.append(f"""
        <tr>
            <td>{_e(nome)}</td>
            <td>{_e(m['empresa'])}</td>
            <td>{_e(m['volume_entregue'])}</td>
            <td>{_fmt_horas(m['cycle_time_medio_horas'])}</td>
            <td class="sp-breakdown">{_e(sp_breakdown)}</td>
        </tr>""")
    return f"""
    <section>
        <h2>Por desenvolvedor</h2>
        <table class="tabela-dev">
            <thead>
                <tr><th>Dev</th><th>Empresa</th><th>Entregues</th><th>Cycle time médio</th><th>Tempo médio por SP</th></tr>
            </thead>
            <tbody>{"".join(linhas)}</tbody>
        </table>
    </section>"""


def _secao_tabela_issues(dataset: list) -> str:
    ordem_estado = {e: i for i, e in enumerate(ESTADO_ORDEM)}
    ordenado = sorted(dataset, key=lambda d: (ordem_estado.get(d["estado_atual"], 99), d.get("titulo") or ""))

    linhas = []
    for d in ordenado:
        linhas.append(f"""
        <tr data-estado="{_e(d['estado_atual'])}" data-tipo="{_e(d.get('tipo'))}">
            <td>{_e(d.get('titulo'))}</td>
            <td>{_badge_estado(d['estado_atual'])}</td>
            <td>{_e(d.get('assignee') or '—')}</td>
            <td>{_e(d.get('story_points') if d.get('story_points') is not None else '—')}</td>
            <td>{_badge_tipo(d.get('tipo'))}</td>
            <td>{_fmt_horas(d.get('cycle_time_horas'))}{' *' if d.get('cycle_time_fallback') else ''}</td>
            <td>{'Sim' if d.get('retrabalho') else '—'}</td>
            <td>{'Sim' if d.get('parado') else '—'}</td>
            <td>{_e(d.get('entrou_finished_em') or '—')}</td>
        </tr>""")

    return f"""
    <section>
        <h2>Tickets ({len(dataset)})</h2>
        <p class="nota">* cycle time calculado com fallback Todo → Done (ticket pulou In Progress).
        Só título — descrição e resolução ficam no dataset completo, fora desta tabela.</p>
        <input type="text" id="filtro-titulo" placeholder="Filtrar por título..." oninput="filtrarTabela()">
        <table class="tabela-issues" id="tabela-issues">
            <thead>
                <tr>
                    <th>Título</th><th>Estado</th><th>Assignee</th><th>SP</th><th>Tipo</th>
                    <th>Cycle time</th><th>Retrabalho</th><th>Parado</th><th>Finished em</th>
                </tr>
            </thead>
            <tbody>{"".join(linhas)}</tbody>
        </table>
    </section>"""


CSS = """
:root {
    --bg: #0f1115; --card: #171a21; --border: #2a2e38; --text: #e6e8ec;
    --text-dim: #9aa1ac; --accent: #5b8def; --ok: #4caf7d; --warn: #d9a441; --bad: #d9534f;
}
* { box-sizing: border-box; }
body { margin:0; padding:0 0 60px; background:var(--bg); color:var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
header { padding: 32px 24px 16px; border-bottom: 1px solid var(--border); }
header h1 { margin:0 0 4px; font-size: 22px; }
header p { margin:0; color: var(--text-dim); font-size: 13px; }
main { max-width: 1100px; margin: 0 auto; padding: 24px; }
section { margin-bottom: 40px; }
h2 { font-size: 16px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-dim);
    border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 16px; }
h3 { font-size: 14px; color: var(--text-dim); margin: 24px 0 12px; }
.kpi-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.kpi-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; text-align:center; }
.kpi-valor { font-size: 32px; font-weight: 700; color: var(--accent); }
.kpi-label { font-size: 13px; margin-top: 4px; }
.kpi-sub { font-size: 11px; color: var(--text-dim); margin-top: 2px; }
.metric-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px,1fr)); gap: 12px; }
.metric-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
.metric-valor { font-size: 20px; font-weight: 600; }
.metric-label { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
.metric-sub { font-size: 11px; color: var(--text-dim); }
.bar-chart { display:flex; flex-direction:column; gap:8px; }
.bar-row { display:flex; align-items:center; gap:10px; font-size:13px; }
.bar-label { width: 70px; color: var(--text-dim); }
.bar-track { flex:1; background: var(--border); border-radius: 4px; height: 14px; overflow:hidden; }
.bar-fill { background: var(--accent); height: 100%; }
.bar-valor { width: 24px; text-align:right; }
.tipo-grid { display:flex; gap: 20px; }
.tipo-item { display:flex; align-items:center; gap:8px; font-size: 14px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
th { color: var(--text-dim); font-weight: 500; }
.sp-breakdown { color: var(--text-dim); font-size: 12px; }
.badge { padding: 2px 8px; border-radius: 999px; font-size: 11px; white-space:nowrap; }
.estado-backlog { background:#2a2e38; color:#9aa1ac; }
.estado-todo { background:#2a3a55; color:#8fb4ff; }
.estado-in-progress { background:#4a3a1f; color:var(--warn); }
.estado-done { background:#1f3d31; color:var(--ok); }
.estado-finished { background:#173d2a; color:#5fd394; }
.estado-cancelled { background:#3d1f1f; color:var(--bad); }
.tipo-bug { background:#3d1f1f; color:var(--bad); }
.tipo-fix { background:#3a3520; color:var(--warn); }
.tipo-feature { background:#1f2d3d; color:var(--accent); }
.nota { font-size: 12px; color: var(--text-dim); }
#filtro-titulo { width:100%; padding:8px 10px; margin-bottom:12px; background:var(--card);
    border:1px solid var(--border); border-radius:6px; color:var(--text); font-size:13px; }
footer { text-align:center; color: var(--text-dim); font-size: 12px; padding: 24px; }
"""

JS = """
function filtrarTabela() {
    const termo = document.getElementById('filtro-titulo').value.toLowerCase();
    document.querySelectorAll('#tabela-issues tbody tr').forEach(tr => {
        const titulo = tr.children[0].textContent.toLowerCase();
        tr.style.display = titulo.includes(termo) ? '' : 'none';
    });
}
"""


def render_html(metrics: dict, dataset: list) -> str:
    gerado_em = tu.format_datetime_br(datetime.now())
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard NBCDM</title>
<style>{CSS}</style>
</head>
<body>
<header>
    <h1>Dashboard NBCDM — Métricas de time (Plane.so)</h1>
    <p>Gerado em {_e(gerado_em)} · {metrics.get('total_issues', 0)} issues no total</p>
</header>
<main>
    {_kpi_cards(metrics['kpis_topo'])}
    {_secao_processo(metrics['processo'])}
    {_secao_por_dev(metrics['por_dev'])}
    {_secao_tabela_issues(dataset)}
</main>
<footer>nb-cdm · dashboard estático, publicado via GitHub Pages · datas em dd/mm/aaaa</footer>
<script>{JS}</script>
</body>
</html>"""


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_html(content: str, path: str = OUTPUT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Dashboard gerado em: {path}")


if __name__ == "__main__":
    print("Carregando métricas e dataset...")
    metrics = load_json(METRICS_PATH)
    dataset = load_json(ISSUES_PATH)
    html_out = render_html(metrics, dataset)
    save_html(html_out)
