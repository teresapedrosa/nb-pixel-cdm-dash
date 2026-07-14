"""
Cliente base da API do Plane.so (self-hosted, plane.pixelbreeders.com).

Endpoints usados:
- GET  .../states/                          → estados do projeto (kanban)
- GET  .../issues/?per_page=100              → issues do projeto (paginado)
- GET  .../issues/{issue_id}/activities/     → histórico de transições (timestamps)
- GET  .../cycles/                           → sprints/cycles
- GET  .../cycles/{cycle_id}/cycle-issues/   → issues de um cycle

Toda a instrumentação de lead time / cycle time depende do endpoint de
activities — é lá que ficam os timestamps de cada mudança de estado.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

PLANE_API_KEY = os.getenv("PLANE_API_KEY")
PLANE_BASE_URL = os.getenv("PLANE_BASE_URL", "https://plane.pixelbreeders.com/api/v1")
PLANE_WORKSPACE_SLUG = os.getenv("PLANE_WORKSPACE_SLUG", "pixel-breeders")
PROJECT_ID = os.getenv("PROJECT_ID")  # confirmar se é novo projeto ou o mesmo

HEADERS = {
    "X-Api-Key": PLANE_API_KEY,
    "Content-Type": "application/json",
}


def _base_url() -> str:
    if not PROJECT_ID:
        raise RuntimeError(
            "PROJECT_ID não configurado no .env. "
            "Confirme se este dashboard aponta para um projeto novo no Plane "
            "ou para o mesmo projeto do dashboard anterior."
        )
    return f"{PLANE_BASE_URL}/workspaces/{PLANE_WORKSPACE_SLUG}/projects/{PROJECT_ID}"


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{_base_url()}{path}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_states() -> list:
    return _get("/states/").get("results", [])


def get_issues(per_page: int = 100) -> list:
    issues = []
    cursor = None
    while True:
        params = {"per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        page = _get("/issues/", params=params)
        issues.extend(page.get("results", []))
        if not page.get("next_page_results"):
            break
        cursor = page.get("next_cursor")
    return issues


def get_issue_activities(issue_id: str) -> list:
    return _get(f"/issues/{issue_id}/activities/").get("results", [])


def get_cycles() -> list:
    return _get("/cycles/").get("results", [])


def get_cycle_issues(cycle_id: str) -> list:
    return _get(f"/cycles/{cycle_id}/cycle-issues/").get("results", [])


def get_project_members() -> list:
    """
    Membros do projeto. Retorna os IDs internos usados como `assignee`
    nos issues, para cruzar com o mapeamento de e-mail em src/team.py.
    Shape confirmado em runtime: id, first_name, last_name, email,
    avatar, avatar_url, display_name.
    """
    data = _get("/members/")
    return data.get("results", data) if isinstance(data, dict) else data


def get_labels() -> list:
    """
    Labels do projeto (inclui `fix` e `bug`). Usadas apenas para
    categorização de tickets nos relatórios — não entram no cálculo
    de retrabalho.
    """
    data = _get("/labels/")
    return data.get("results", data) if isinstance(data, dict) else data
