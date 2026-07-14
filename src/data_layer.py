"""
Passo 2/3 — Camada de dados.

Busca issues, activities, membros e labels na API do Plane, e monta um
dataset consolidado (uma linha por issue) com todos os timestamps e
métricas de tempo já calculados. Esse dataset é a base para as métricas
do Passo 3 (metrics.py) e para o dashboard do Passo 4.

Cache incremental (Passo 3): activities de issues cujo `updated_at` não
mudou desde o último sync são reaproveitadas do cache local em vez de
rebuscadas — ver src/cache.py para a lógica e a regra de needs_retry.

Uso:
    python -m src.data_layer          # sync incremental, salva em data/issues.json
    python -m src.data_layer --full   # ignora cache, rebusca activities de tudo
"""

import os
import sys
import json
from datetime import datetime

from . import plane_client as pc
from . import team
from . import labels as story_labels
from . import time_utils as tu
from . import cache

STUCK_THRESHOLD_HOURS = float(os.getenv("STUCK_THRESHOLD_HOURS", 16))
WORK_HOURS_PER_DAY = int(os.getenv("WORK_HOURS_PER_DAY", 8))

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "issues.json")


def _state_name_map(states: list) -> dict:
    return {s["id"]: s["name"] for s in states}


def _extract_state_history(activities: list, state_names: dict) -> list:
    """
    Retorna lista ordenada de transições de estado: [{"from": ..., "to": ..., "at": datetime}, ...]
    A partir de activities com field == "state" (old_value/new_value são
    UUIDs de estado).
    """
    history = []
    for a in activities:
        if a.get("field") != "state":
            continue
        from_id = a.get("old_value")
        to_id = a.get("new_value")
        history.append({
            "from": state_names.get(from_id, from_id),
            "to": state_names.get(to_id, to_id),
            "at": tu.parse_iso(a["created_at"]) if a.get("created_at") else None,
        })
    history.sort(key=lambda h: h["at"] or datetime.min.replace(tzinfo=None))
    return history


def _first_entry(history: list, state_name: str):
    for h in history:
        if h["to"] == state_name:
            return h["at"]
    return None


def _was_reopened_from(history: list, from_states: set, to_states: set) -> bool:
    """True se em algum momento o issue saiu de um estado em `from_states` para um em `to_states`."""
    for h in history:
        if h["from"] in from_states and h["to"] in to_states:
            return True
    return False


def _compute_record(issue: dict, activities: list, state_name: str, state_names: dict, label_index: dict) -> dict:
    """
    Calcula o registro consolidado de um issue a partir das activities já
    resolvidas (frescas ou reaproveitadas do cache). Separado da busca de
    activities de propósito: a lógica de negócio pode mudar e ser
    recalculada sem precisar rebuscar nada na API.
    """
    history = _extract_state_history(activities, state_names)

    created_at = tu.parse_iso(issue["created_at"]) if issue.get("created_at") else None
    first_todo = _first_entry(history, "Todo")
    first_in_progress = _first_entry(history, "In Progress")
    first_done = _first_entry(history, "Done")
    first_finished = _first_entry(history, "Finished")

    # Lead time: criação → Finished (ponto final real do ticket)
    lead_time_hours = tu.hours_between(created_at, first_finished)

    # Cycle time: primeiro In Progress → Done, com fallback para Todo → Done
    # quando o ticket pulou o estado In Progress.
    cycle_time_hours = None
    cycle_time_fallback = False
    if first_in_progress and first_done:
        cycle_time_hours = tu.hours_between(first_in_progress, first_done)
    elif first_todo and first_done:
        cycle_time_hours = tu.hours_between(first_todo, first_done)
        cycle_time_fallback = True

    # Tempo de homologação NewByte: Done → Finished
    homologation_hours = tu.hours_between(first_done, first_finished)

    # Retrabalho: reabertura de Done/Finished para Todo/In Progress, OU
    # issue vinculado a outro (campo parent).
    reopened = _was_reopened_from(
        history,
        from_states={"Done", "Finished"},
        to_states={"Todo", "In Progress"},
    )
    has_parent_link = bool(issue.get("parent"))
    retrabalho = reopened or has_parent_link

    # Story points e categorização (via labels)
    sp = story_labels.get_issue_sp(issue, label_index)
    oversized = story_labels.is_oversized(issue, label_index)
    tipo = story_labels.get_issue_type(issue, label_index)

    # Assignee (só o primeiro — issues deste projeto normalmente têm 1)
    assignee_ids = issue.get("assignees", []) or []
    assignee = None
    assignee_fora_do_roster = False
    if assignee_ids:
        resolved = team.get_member_by_uuid(assignee_ids[0])
        if resolved:
            assignee = resolved["nome"]
        else:
            assignee_fora_do_roster = True

    # Issue parado: em Todo ou In Progress há mais de STUCK_THRESHOLD_HOURS,
    # sem ainda ter chegado em Done.
    stuck = False
    if state_name in ("Todo", "In Progress"):
        anchor = first_in_progress or first_todo
        if anchor:
            elapsed = tu.hours_between(anchor, datetime.now(anchor.tzinfo))
            stuck = elapsed is not None and elapsed > STUCK_THRESHOLD_HOURS

    return {
        "id": issue["id"],
        "titulo": issue.get("name"),
        "estado_atual": state_name,
        "assignee": assignee,
        "assignee_fora_do_roster": assignee_fora_do_roster,
        "story_points": sp,
        "oversized": oversized,
        "tipo": tipo,
        "criado_em": tu.format_date_br(created_at),
        "entrou_todo_em": tu.format_date_br(first_todo),
        "entrou_in_progress_em": tu.format_date_br(first_in_progress),
        "entrou_done_em": tu.format_date_br(first_done),
        "entrou_finished_em": tu.format_date_br(first_finished),
        "lead_time_horas": lead_time_hours,
        "cycle_time_horas": cycle_time_hours,
        "cycle_time_fallback": cycle_time_fallback,
        "homologacao_horas": homologation_hours,
        "retrabalho": retrabalho,
        "retrabalho_por_reabertura": reopened,
        "retrabalho_por_vinculo": has_parent_link,
        "parado": stuck,
    }


def build_dataset(use_cache: bool = True) -> list:
    states = pc.get_states()
    state_names = _state_name_map(states)

    members = pc.get_project_members()
    team.build_assignee_map(members)

    project_labels = pc.get_labels()
    label_index = story_labels.build_label_index(project_labels)

    issues = pc.get_issues()

    cache_data = cache.load_cache() if use_cache else {}
    reused = refetched = retried = skipped_backlog = 0

    dataset = []
    total = len(issues)
    for idx, issue in enumerate(issues, start=1):
        issue_id = issue["id"]
        state_id = issue.get("state")
        state_name = state_names.get(state_id)
        cached_entry = cache_data.get(issue_id)

        if state_name == "Backlog":
            # Issues que nunca saíram do Backlog não têm cronômetro rodando —
            # ainda entram no dataset (contagem de backlog), mas sem gastar
            # uma chamada de activities. Não grava no cache incremental
            # (se sair do Backlog depois, precisa ser buscado do zero).
            activities = []
            skipped_backlog += 1
        elif use_cache and not cache.needs_refetch(issue, cached_entry):
            activities = cached_entry["activities"]
            reused += 1
        else:
            activities, status = cache.fetch_activities_safe(pc, issue_id)
            if status == cache.STATUS_NEEDS_RETRY and cached_entry:
                # Falha na busca: mantém as activities antigas no dataset
                # (melhor que zerar métricas de um issue já processado
                # antes), mas o cache fica marcado needs_retry pra
                # garantir nova tentativa no próximo sync.
                activities = cached_entry.get("activities", [])
            cache_data[issue_id] = {
                "_updated_at": issue.get("updated_at"),
                "_status": status,
                "activities": activities,
            }
            if status == cache.STATUS_OK:
                refetched += 1
            else:
                retried += 1

        record = _compute_record(issue, activities, state_name, state_names, label_index)
        dataset.append(record)

        if idx % 20 == 0 or idx == total:
            print(f"    Processado {idx}/{total} issues...")

    if use_cache:
        cache.save_cache(cache_data)
        print(
            f"Cache: {reused} reaproveitados, {refetched} rebuscados, "
            f"{retried} com falha (needs_retry), {skipped_backlog} em backlog (sem activities)"
        )

    return dataset


def save_dataset(dataset: list, path: str = DATA_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2, default=str)
    print(f"Dataset salvo em: {path} ({len(dataset)} issues)")


def load_dataset(path: str = DATA_PATH) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    use_cache = "--full" not in sys.argv
    if not use_cache:
        print("Modo --full: ignorando cache incremental, rebuscando activities de tudo.")

    print("Buscando dados na API do Plane e montando dataset...")
    ds = build_dataset(use_cache=use_cache)
    save_dataset(ds)

    print("\n--- Resumo rápido ---")
    print(f"Total de issues: {len(ds)}")
    print(f"Com story point: {sum(1 for d in ds if d['story_points'] is not None)}")
    print(f"Oversized (SP 13+): {sum(1 for d in ds if d['oversized'])}")
    print(f"Com retrabalho: {sum(1 for d in ds if d['retrabalho'])}")
    print(f"Parados (acima de {STUCK_THRESHOLD_HOURS}h): {sum(1 for d in ds if d['parado'])}")
    print(f"Cycle time com fallback (pulou In Progress): {sum(1 for d in ds if d['cycle_time_fallback'])}")
    print(f"Assignee fora do roster: {sum(1 for d in ds if d['assignee_fora_do_roster'])}")
