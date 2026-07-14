"""
Resolução de labels do projeto NBCDM.

Neste projeto, story points NÃO usam o campo `estimate_point` do Work Item —
são representados como labels: "SP 01", "SP 02", "SP 03", "SP 05", "SP 08",
"SP 13+". As labels "fix" e "bug" são categorização de tipo de ticket
(não contam como retrabalho — ver README).
"""

import re

SP_LABEL_RE = re.compile(r"^SP\s*(\d+)\+?$", re.IGNORECASE)

# "SP 13+" não é um nível fixo de story point — é o sinalizador de que o
# ticket estourou a escala e deve ser tratado como "issue grande demais".
OVERSIZED_LABEL = "SP 13+"


def build_label_index(labels: list) -> dict:
    """{label_id: nome_da_label} a partir de get_labels()."""
    return {l["id"]: l.get("name", "") for l in labels}


def get_issue_sp(issue: dict, label_index: dict) -> int | None:
    """
    Retorna o valor numérico do story point do issue (01, 02, 03, 05, 08),
    ou None se não tiver label de SP ou se for SP 13+ (tratado como
    oversized, não como nível de SP regular).
    """
    for label_id in issue.get("labels", []) or []:
        name = label_index.get(label_id, "")
        if name.strip().upper() == OVERSIZED_LABEL.upper():
            return None
        m = SP_LABEL_RE.match(name.strip())
        if m:
            return int(m.group(1))
    return None


def is_oversized(issue: dict, label_index: dict) -> bool:
    """True se o issue tiver a label 'SP 13+' — candidato a 'issue grande demais'."""
    names = {label_index.get(lid, "").strip().upper() for lid in issue.get("labels", []) or []}
    return OVERSIZED_LABEL.upper() in names


def get_issue_type(issue: dict, label_index: dict) -> str:
    """Retorna 'bug', 'fix' ou 'feature' (default) — categorização, não retrabalho."""
    names = {label_index.get(lid, "").strip().lower() for lid in issue.get("labels", []) or []}
    if "bug" in names:
        return "bug"
    if "fix" in names:
        return "fix"
    return "feature"
