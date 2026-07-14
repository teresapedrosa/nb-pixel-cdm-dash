"""
Passo 1 — Validação da conexão com a API do Plane.

Roda um diagnóstico rápido: autenticação, estados, issues, shape das
activities (fonte dos timestamps), membros do projeto (resolução de
assignee) e uso do campo `parent` para detectar retrabalho por vínculo
(não há endpoint público de issue-relation na API do Plane).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import plane_client as pc
from src import team
from src import labels as story_labels


def main():
    print("=" * 60)
    print("TESTE DE CONEXÃO — Plane.so")
    print("=" * 60)

    print("\n[1] Estados do projeto")
    states = pc.get_states()
    for s in states:
        print(f"    - {s.get('name')} (id: {s.get('id')})")
    state_names = {s.get("name") for s in states}
    if not {"QA", "Verified"} & state_names:
        print("    [!] Sem QA/Verified — retrabalho definido por reabertura de Done/Finished e/ou vínculo via `parent` (ver README).")
    if "Finished" not in state_names:
        print("    [!] Estado 'Finished' não encontrado — confirmar se já foi criado no Plane.")

    print("\n[2] Issues do projeto")
    issues = pc.get_issues()
    print(f"    Total: {len(issues)} issues")

    # Preferir "Finished" (ponto final real do ticket) para a amostra;
    # cair para "Done" se ainda não houver nenhum Finished.
    done_state = next((s["id"] for s in states if s.get("name") == "Done"), None)
    finished_state = next((s["id"] for s in states if s.get("name") == "Finished"), None)
    done_issues = [i for i in issues if i.get("state") == done_state]
    finished_issues = [i for i in issues if i.get("state") == finished_state] if finished_state else []
    print(f"    Issues em Done: {len(done_issues)}")
    print(f"    Issues em Finished: {len(finished_issues)}")
    sample_pool = finished_issues or done_issues

    print("\n[3] Activities de um issue já concluído (Finished, se houver — não issues[0])")
    if sample_pool:
        sample = sample_pool[0]
        print(f"    Amostra: {sample.get('name')}")
        activities = pc.get_issue_activities(sample["id"])
        state_changes = [a for a in activities if a.get("field") == "state"]
        print(f"    Total de activities: {len(activities)}")
        print(f"    Transições de estado: {len(state_changes)}")
        for a in state_changes[:8]:
            print(f"      {a.get('old_value')} → {a.get('new_value')} @ {a.get('created_at')}")
    else:
        print("    Nenhum issue em Done/Finished ainda — não é possível validar timestamps completos.")

    print("\n[4] Cycles (sprints)")
    cycles = pc.get_cycles()
    if not cycles:
        print("    Nenhum cycle encontrado — throughput será calculado por período de calendário (semana/mês), não por sprint do Plane.")
    for c in cycles[:5]:
        print(f"    - {c.get('name')} ({c.get('start_date')} → {c.get('end_date')})")

    print("\n[5] Membros do projeto (resolução de assignee)")
    try:
        members = pc.get_project_members()
        print(f"    Total de membros retornados: {len(members)}")
        if members:
            print(f"    Shape de um membro (ajustar team.py.build_assignee_map se necessário):")
            print(f"      {members[0]}")
        resolved = team.build_assignee_map(members)
        print(f"    Resolvidos por e-mail: {len(resolved)} / {len(members)}")
        unresolved = team.unresolved_team_members(members)
        if unresolved:
            nomes = [u["nome"] for u in unresolved]
            print(f"    [!] Do roster (team.py), NÃO encontrados como membros do projeto: {nomes}")
    except Exception as e:
        print(f"    [ERRO] Não foi possível buscar membros: {e}")
        members = []

    print("\n[6] Cobertura do mapeamento de time nos issues")
    assignee_ids = set()
    for i in issues:
        for a in i.get("assignees", []) or []:
            assignee_ids.add(a)
    mapeados = [aid for aid in assignee_ids if team.get_member_by_uuid(aid)]
    nao_mapeados = [aid for aid in assignee_ids if not team.get_member_by_uuid(aid)]
    print(f"    Assignees encontrados nos issues: {len(assignee_ids)}")
    print(f"    Mapeados (via e-mail): {len(mapeados)}")
    if nao_mapeados:
        by_id = {m.get("id"): m for m in members}
        for aid in nao_mapeados:
            info = by_id.get(aid)
            if info:
                print(f"    NÃO mapeado: {aid} → {info.get('first_name')} {info.get('last_name')} ({info.get('email')}) — membro do projeto, fora do roster de team.py")
            else:
                print(f"    NÃO mapeado: {aid} → não encontrado nem na lista de membros do projeto")

    print("\n[7] Retrabalho por vínculo — usando campo `parent` (não há endpoint de issue-relation na API pública)")
    vinculados = [i for i in issues if i.get("parent")]
    print(f"    Issues com `parent` preenchido: {len(vinculados)} / {len(issues)}")
    if vinculados:
        exemplo = vinculados[0]
        print(f"    Exemplo: '{exemplo.get('name')}' → parent: {exemplo.get('parent')}")

    print("\n[8] Labels do projeto (categorização — fix/bug não contam como retrabalho)")
    try:
        labels = pc.get_labels()
        print(f"    Total de labels: {len(labels)}")
        for l in labels:
            print(f"    - {l.get('name')} (id: {l.get('id')})")
        fix_bug = {"fix", "bug"} & {l.get("name", "").lower() for l in labels}
        if not fix_bug:
            print("    [!] Labels 'fix'/'bug' não encontradas — confirmar nome exato usado no Plane.")

        label_index = story_labels.build_label_index(labels)
        sp_counts = {}
        oversized = []
        tipo_counts = {"bug": 0, "fix": 0, "feature": 0}
        for i in issues:
            sp = story_labels.get_issue_sp(i, label_index)
            if sp is not None:
                sp_counts[sp] = sp_counts.get(sp, 0) + 1
            if story_labels.is_oversized(i, label_index):
                oversized.append(i.get("name"))
            tipo_counts[story_labels.get_issue_type(i, label_index)] += 1

        print(f"    Distribuição de SP (via labels): {dict(sorted(sp_counts.items()))}")
        print(f"    Issues 'SP 13+' (oversized): {len(oversized)}")
        print(f"    Distribuição por tipo: {tipo_counts}")
    except Exception as e:
        print(f"    [ERRO] Não foi possível buscar labels: {e}")

    print("\n" + "=" * 60)
    print("Teste concluído.")
    print("=" * 60)


if __name__ == "__main__":
    main()
