"""
Passo 3 — Agregação de métricas.

Lê o dataset consolidado (uma linha por issue, gerado por data_layer.py)
e agrega nas métricas definidas no README: 3 KPIs de topo, métricas de
processo, quebra por tipo e métricas por desenvolvedor. Salva o resultado
em data/metrics.json — é esse arquivo que o Passo 4 (dashboard estático)
consome, sem precisar recalcular nada.

Uso:
    python -m src.metrics             # lê data/issues.json, salva data/metrics.json
"""

import os
import json
import statistics as st

from . import team

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "issues.json")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metrics.json")

FINISHED_STATES_ABERTOS_EXCLUIDOS = {"Finished", "Cancelled"}


def _avg(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(st.mean(values), 2) if values else None


def _median(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(st.median(values), 2) if values else None


def _month_key(data_br: str) -> str | None:
    """'14/07/2026' -> '2026-07' (chave ordenável para agrupar por mês)."""
    if not data_br:
        return None
    dia, mes, ano = data_br.split("/")
    return f"{ano}-{mes}"


def kpis_topo(dataset: list) -> dict:
    finished = [d for d in dataset if d.get("entrou_finished_em")]
    sp_entregues = sum(d["story_points"] for d in finished if d.get("story_points") is not None)
    em_aberto = [d for d in dataset if d["estado_atual"] not in FINISHED_STATES_ABERTOS_EXCLUIDOS]
    return {
        "tickets_concluidos": len(finished),
        "story_points_entregues": sp_entregues,
        "tickets_em_aberto": len(em_aberto),
    }


def metricas_processo(dataset: list) -> dict:
    lead_times = [d["lead_time_horas"] for d in dataset if d.get("lead_time_horas") is not None]
    cycle_reais = [d["cycle_time_horas"] for d in dataset if d.get("cycle_time_horas") is not None and not d.get("cycle_time_fallback")]
    cycle_fallback = [d["cycle_time_horas"] for d in dataset if d.get("cycle_time_horas") is not None and d.get("cycle_time_fallback")]
    homologacoes = [d["homologacao_horas"] for d in dataset if d.get("homologacao_horas") is not None]

    throughput_por_mes = {}
    for d in dataset:
        mk = _month_key(d.get("entrou_finished_em"))
        if mk:
            throughput_por_mes[mk] = throughput_por_mes.get(mk, 0) + 1

    tipo_counts = {"bug": 0, "fix": 0, "feature": 0}
    for d in dataset:
        tipo_counts[d.get("tipo", "feature")] = tipo_counts.get(d.get("tipo", "feature"), 0) + 1

    total = len(dataset)
    com_retrabalho = sum(1 for d in dataset if d.get("retrabalho"))

    return {
        "lead_time_horas": {"media": _avg(lead_times), "mediana": _median(lead_times), "n": len(lead_times)},
        "cycle_time_horas": {
            "media": _avg(cycle_reais),
            "mediana": _median(cycle_reais),
            "n": len(cycle_reais),
            "com_fallback_todo_done": {"media": _avg(cycle_fallback), "n": len(cycle_fallback)},
        },
        "homologacao_horas": {"media": _avg(homologacoes), "mediana": _median(homologacoes), "n": len(homologacoes)},
        "throughput_por_mes": dict(sorted(throughput_por_mes.items())),
        "wip": sum(1 for d in dataset if d["estado_atual"] == "In Progress"),
        "retrabalho": {
            "total": com_retrabalho,
            "percentual": round(100 * com_retrabalho / total, 1) if total else 0,
            "por_reabertura": sum(1 for d in dataset if d.get("retrabalho_por_reabertura")),
            "por_vinculo": sum(1 for d in dataset if d.get("retrabalho_por_vinculo")),
        },
        "parados": sum(1 for d in dataset if d.get("parado")),
        "oversized_sp13_mais": sum(1 for d in dataset if d.get("oversized")),
        "quebra_por_tipo": tipo_counts,
    }


def metricas_por_dev(dataset: list) -> dict:
    """
    Só para membros com papel 'dev' (team.devs()) — PMs/POs não entram
    aqui, só nas atribuições de acompanhamento (conforme README).

    Só devs da Pixel (`team.pixel_devs()`) — decisão do dashboard nb-cdm:
    a visão publicada é "só Pixel". NewByte fica fora dos cards por dev.
    """
    resultado = {}
    for slug, info in team.pixel_devs().items():
        nome = info["nome"]
        issues_dev = [d for d in dataset if d.get("assignee") == nome]
        finished_dev = [d for d in issues_dev if d.get("entrou_finished_em")]
        cycle_times = [d["cycle_time_horas"] for d in issues_dev if d.get("cycle_time_horas") is not None]

        por_sp = {}
        for d in issues_dev:
            sp = d.get("story_points")
            ct = d.get("cycle_time_horas")
            if sp is not None and ct is not None:
                por_sp.setdefault(sp, []).append(ct)
        tempo_medio_por_sp = {str(sp): _avg(vals) for sp, vals in sorted(por_sp.items())}

        resultado[nome] = {
            "empresa": info["empresa"],
            "cargo": info["cargo"],
            "volume_entregue": len(finished_dev),
            "cycle_time_medio_horas": _avg(cycle_times),
            "tempo_medio_horas_por_story_point": tempo_medio_por_sp,
        }
    return resultado


def build_metrics(dataset: list, total_issues_todos: int | None = None) -> dict:
    """
    `dataset` já deve vir filtrado pro escopo publicado (ver
    team.filter_pixel_dataset). `total_issues_todos`, se informado, guarda
    o total antes do filtro — só pra contexto no rodapé do dashboard.
    """
    return {
        "kpis_topo": kpis_topo(dataset),
        "processo": metricas_processo(dataset),
        "por_dev": metricas_por_dev(dataset),
        "total_issues": len(dataset),
        "total_issues_todos": total_issues_todos if total_issues_todos is not None else len(dataset),
    }


def save_metrics(metrics: dict, path: str = METRICS_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=str)
    print(f"Métricas salvas em: {path}")


def load_dataset(path: str = DATA_PATH) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    print("Carregando dataset e agregando métricas...")
    ds_completo = load_dataset()
    ds = team.filter_pixel_dataset(ds_completo)
    print(f"Filtro Pixel-only: {len(ds)}/{len(ds_completo)} issues (visão publicada)")
    metrics = build_metrics(ds, total_issues_todos=len(ds_completo))
    save_metrics(metrics)

    print("\n--- KPIs de topo ---")
    for k, v in metrics["kpis_topo"].items():
        print(f"  {k}: {v}")

    print("\n--- Processo ---")
    p = metrics["processo"]
    print(f"  Lead time médio: {p['lead_time_horas']['media']}h (n={p['lead_time_horas']['n']})")
    print(f"  Cycle time médio: {p['cycle_time_horas']['media']}h (n={p['cycle_time_horas']['n']})")
    print(f"  Homologação média: {p['homologacao_horas']['media']}h (n={p['homologacao_horas']['n']})")
    print(f"  WIP: {p['wip']}")
    print(f"  Retrabalho: {p['retrabalho']['total']} ({p['retrabalho']['percentual']}%)")
    print(f"  Parados: {p['parados']}")
    print(f"  Oversized (SP 13+): {p['oversized_sp13_mais']}")
    print(f"  Quebra por tipo: {p['quebra_por_tipo']}")

    print("\n--- Por dev ---")
    for nome, m in metrics["por_dev"].items():
        print(f"  {nome} ({m['empresa']}): {m['volume_entregue']} entregues, cycle time médio {m['cycle_time_medio_horas']}h")
