"""
Passo 3 — Cache incremental de activities por issue.

O endpoint de activities (`get_issue_activities`) é uma chamada por issue —
caro em projetos grandes. Este módulo evita rebuscar activities de issues
que não mudaram desde o último sync, comparando o `updated_at` retornado
pela API contra o valor salvo no cache local (`data/issues_cache.json`).

Regra importante: se uma busca falhar (rate limit, timeout, erro de rede),
o issue é marcado com status "needs_retry" — nunca vira um registro vazio
silencioso. Um cache incremental por `updated_at` só refaz a busca quando
o valor muda; se uma falha virasse "vazio" sem sinalização, esse vazio
ficaria congelado pra sempre, porque nada mais tocaria o `updated_at` do
issue pra forçar nova tentativa. Por isso "vazio genuíno" (issue sem
activities mesmo) e "falha ao buscar" são estados diferentes no cache.

Uso típico (dentro de data_layer.py):
    cache_data = load_cache()
    entry = cache_data.get(issue_id)
    if needs_refetch(issue, entry):
        activities, status = fetch_activities_safe(plane_client, issue_id)
        cache_data[issue_id] = {
            "_updated_at": issue["updated_at"],
            "_status": status,
            "activities": activities,
        }
    else:
        activities = entry["activities"]
    ...
    save_cache(cache_data)
"""

import os
import json
import time

import requests

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "issues_cache.json")

# Delay simples entre chamadas de API, pra não estourar rate limit.
# Se no futuro isso passar a rodar em threads paralelas, trocar por um
# throttle/semaphore compartilhado entre workers em vez de sleep sequencial
# — múltiplas threads sem throttle comum é o jeito clássico de estourar
# o limite mesmo com delay configurado em cada uma isoladamente.
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "0.2"))

STATUS_OK = "ok"
STATUS_NEEDS_RETRY = "needs_retry"


def load_cache(path: str = CACHE_PATH) -> dict:
    """{issue_id: {"_updated_at": ..., "_status": ..., "activities": [...]}}"""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache_data: dict, path: str = CACHE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)


def needs_refetch(issue: dict, cached_entry: dict | None) -> bool:
    """
    True se as activities do issue precisam ser rebuscadas:
    - nunca foram buscadas antes (sem entrada no cache);
    - a última tentativa falhou (needs_retry) — sempre retenta,
      independente do updated_at ter mudado ou não;
    - o `updated_at` da API mudou desde o último sync bem-sucedido.
    """
    if cached_entry is None:
        return True
    if cached_entry.get("_status") == STATUS_NEEDS_RETRY:
        return True
    return cached_entry.get("_updated_at") != issue.get("updated_at")


def throttle():
    time.sleep(REQUEST_DELAY_SECONDS)


def fetch_activities_safe(plane_client_module, issue_id: str) -> tuple[list, str]:
    """
    Busca activities de um issue com tratamento de falha.
    Retorna (activities, status) — status é STATUS_OK ou STATUS_NEEDS_RETRY.
    Nunca deixa uma falha de rede virar silenciosamente uma lista vazia
    sem sinalização (ver docstring do módulo).
    """
    try:
        throttle()
        activities = plane_client_module.get_issue_activities(issue_id)
        return activities, STATUS_OK
    except requests.exceptions.RequestException as e:
        print(f"    [AVISO] Falha ao buscar activities de {issue_id}: {e}")
        return [], STATUS_NEEDS_RETRY
