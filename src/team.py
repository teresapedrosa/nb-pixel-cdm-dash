"""
Mapeamento do time — Dashboard NB/Pixel

Fonte da verdade para converter o `assignee` (plane-id / e-mail) retornado
pela API do Plane.so em informações legíveis do time: nome, empresa,
cargo e papel no processo.

Papéis considerados na instrumentação:
- "dev": entra nas métricas de cycle time, throughput e story points.
- "pm": acompanha e consolida métricas. Não entra nas métricas de dev.
- "po": decisão final. Não participa do dia a dia, não entra nas métricas de dev.
"""

TEAM = {
    # NOTA: Arthur Stein (arthur@newbyte.net.br) aparece como assignee em
    # tickets deste projeto, mas foi excluído deliberadamente do roster —
    # não faz parte do time mapeado neste dashboard. Tickets atribuídos a
    # ele ficam fora das métricas de dev (SP, cycle time, throughput
    # individual), mas ainda contam nas métricas agregadas do projeto.
    "fabricio": {
        "nome": "Fafis",
        "discord_tag": "Fafis:wrench:",
        "empresa": "Pixel",
        "cargo": "CEO",
        "email": "fabricio@pixelbreeders.com",
        "papel": "po",
    },
    "tiago": {
        "nome": "Tiago",
        "discord_tag": "Tiago:briefcase:",
        "empresa": "NewByte",
        "cargo": "CTO - PO",
        "email": "tiago@newbyte.net.br",
        "papel": "po",
    },
    "felipe.chemin": {
        "nome": "Felipe Chemin",
        "discord_tag": "Felipe Chemin (Projetos Internos)",
        "empresa": "NewByte",
        "cargo": "Dev - PI",
        "email": "felipe.chemin@newbyte.net.br",
        "papel": "dev",
    },
    "rosa.arthurh": {
        "nome": "Arthur",
        "discord_tag": "Arthur",
        "empresa": "Pixel",
        "cargo": "Dev",
        "email": "rosa.arthurh@gmail.com",
        "papel": "dev",
    },
    "marcosdamata2000": {
        "nome": "Marcos",
        "discord_tag": "Marcos",
        "empresa": "Pixel",
        "cargo": "Dev",
        "email": "marcosdamata2000@gmail.com",
        "papel": "dev",
    },
    "artur.ritzel": {
        "nome": "Ritzel",
        "discord_tag": "Ritzel [n8n] (Projetos Internos)",
        "empresa": "NewByte",
        "cargo": "Dev - PI",
        "email": "artur.ritzel@newbyte.net.br",
        "papel": "dev",
    },
    "giovanna": {
        "nome": "GiPipolo",
        "discord_tag": "GiPipolo",
        "empresa": "Pixel",
        "cargo": "Lead PM",
        "email": "giovanna@pixelbreeders.com",
        "papel": "pm",
    },
    "teresa": {
        "nome": "Teresa",
        "discord_tag": "teresa:wrench:",
        "empresa": "Pixel",
        "cargo": "PM",
        "email": "teresadefreitaspedrosa@gmail.com",
        "papel": "pm",
    },
    "caua.mendes": {
        "nome": "Cauã Puppim",
        "discord_tag": "Cauã Puppim:wrench:",
        "empresa": "NewByte",
        "cargo": "PM - PI",
        "email": "caua.mendes@newbyte.net.br",
        "papel": "pm",
    },
}


def get_member(plane_id: str) -> dict | None:
    """Retorna os dados do membro a partir do slug interno usado neste arquivo."""
    return TEAM.get(plane_id)


def devs() -> dict:
    """Retorna apenas os membros com papel 'dev' — usados nas métricas de SP/cycle time."""
    return {k: v for k, v in TEAM.items() if v["papel"] == "dev"}


def pixel_devs() -> dict:
    """Subconjunto de devs da Pixel — foco declarado do dashboard."""
    return {k: v for k, v in devs().items() if v["empresa"] == "Pixel"}


# ---------------------------------------------------------------------------
# Resolução de UUID da API → membro do time
#
# A API do Plane identifica assignees por UUID interno (ex: "1df20313-..."),
# não pelos slugs usados acima. A validação em tests/test_connection.py
# confirmou isso: os 4 assignees encontrados nos issues não batem com
# nenhuma chave de TEAM.
#
# A resolução correta é: buscar os membros do projeto via
# plane_client.get_project_members() (retorna UUID + e-mail) e cruzar
# com o e-mail já mapeado em TEAM. Isso evita depender de UUIDs
# hardcoded, que podem mudar entre workspaces.
# ---------------------------------------------------------------------------

_ASSIGNEE_MAP: dict[str, dict] = {}


def build_assignee_map(members: list) -> dict:
    """
    Recebe a lista bruta de `get_project_members()` e retorna um dict
    {uuid_da_api: registro_do_TEAM}, casando por e-mail.

    Membros da API sem e-mail correspondente em TEAM são ignorados
    (não fazem parte do time mapeado neste dashboard).
    O shape exato de cada `member` na resposta da API ainda precisa ser
    confirmado — ajustar as chaves de acesso abaixo (`email`, `member__email`,
    `id`, etc.) conforme o retorno real de get_project_members().
    """
    by_email = {v["email"].lower(): v for v in TEAM.values()}
    resolved = {}
    for m in members:
        email = (m.get("email") or m.get("member__email") or "").lower()
        uuid = m.get("id") or m.get("member") or m.get("member_id")
        if email in by_email and uuid:
            resolved[uuid] = by_email[email]
    _ASSIGNEE_MAP.update(resolved)
    return resolved


def get_member_by_uuid(uuid: str) -> dict | None:
    """Retorna o registro do time a partir do UUID retornado pela API de issues."""
    return _ASSIGNEE_MAP.get(uuid)


def unresolved_team_members(members: list) -> list:
    """
    Retorna os registros de TEAM cujo e-mail NÃO aparece na lista de membros
    do projeto (retornada por get_project_members()). Útil para diagnosticar
    gente do roster que ainda não foi adicionada ao projeto no Plane.
    """
    project_emails = {(m.get("email") or "").lower() for m in members}
    return [v for v in TEAM.values() if v["email"].lower() not in project_emails]
