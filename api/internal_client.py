"""
Cliente HTTP pras rotas internas do Flask (web/routes/internal.py).

Por quê: add_job/remove_job/run_job dependem de um singleton `_scheduler`
(APScheduler) vivo só no processo Flask. Chamar por HTTP em vez de
importar `shopee_bot.scheduler` direto evita rodar `scheduler.init()`
duas vezes (dois processos publicando o mesmo job em duplicata) — ver
docstring de web/routes/internal.py e Fase 8 em docs/ROADMAP_MIGRACAO.md.
"""

import logging
import os

import httpx

logger = logging.getLogger("uvicorn.error")

FLASK_INTERNAL_URL = os.environ.get(
    "FLASK_INTERNAL_URL", f"http://127.0.0.1:{os.environ.get('PORT', '5000')}"
)
INTERNAL_API_SECRET = os.environ.get("INTERNAL_API_SECRET", "")
if not INTERNAL_API_SECRET:
    # ponytail: sem conceito de "modo produção" detectável no projeto (ver
    # api/config.py) pra fail-fast seguro — warning visível no import é o
    # que já se faz aqui (mesmo padrão de api/instagram_oauth.py com
    # INSTAGRAM_APP_ID ausente). Sem isso, todo request pro bridge interno
    # falha com 403 disperso e sem pista da causa raiz.
    logger.warning(
        "INTERNAL_API_SECRET não configurado — bridge interno Flask<->FastAPI "
        "vai falhar com 403 em toda chamada (web/routes/internal.py bloqueia "
        "segredo vazio/incorreto)."
    )


class InternalApiError(Exception):
    pass


def _headers() -> dict:
    return {"X-Internal-Secret": INTERNAL_API_SECRET}


async def create_scheduler_job(user_id: str, post_id: int, func: str, trigger: str, **fields) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{FLASK_INTERNAL_URL}/internal/scheduler/jobs",
            json={"user_id": user_id, "post_id": post_id, "func": func, "trigger": trigger, **fields},
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise InternalApiError(f"create_scheduler_job falhou: {resp.status_code} {resp.text}")
    return resp.json()["job_id"]


async def remove_scheduler_job(user_id: str, job_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.request(
            "DELETE",
            f"{FLASK_INTERNAL_URL}/internal/scheduler/jobs/{job_id}",
            json={"user_id": user_id},
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise InternalApiError(f"remove_scheduler_job falhou: {resp.status_code} {resp.text}")


async def run_scheduler_job(job_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{FLASK_INTERNAL_URL}/internal/scheduler/jobs/{job_id}/run",
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise InternalApiError(f"run_scheduler_job falhou: {resp.status_code} {resp.text}")


async def validate_shopee_credential(app_id: str, secret: str) -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{FLASK_INTERNAL_URL}/internal/shopee/validate",
            json={"app_id": app_id, "secret": secret},
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise InternalApiError(f"validate_shopee_credential falhou: {resp.status_code} {resp.text}")
    return bool(resp.json().get("valid"))


async def validate_network_credential(network: str, payload: dict) -> dict:
    """Chama o teste de conexão real (apis/*.py) via bridge interno pro
    botão "Testar conexão" (admin-only). Retorna {"state": "ok"|"error",
    "message": str} — nunca levanta por causa do RESULTADO do teste (uma
    credencial inválida é 'error', não uma InternalApiError); só levanta se
    o bridge em si falhar (Flask fora do ar, segredo errado)."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{FLASK_INTERNAL_URL}/internal/credentials/{network}/validate",
            json=payload,
            headers=_headers(),
        )
    if resp.status_code >= 400:
        raise InternalApiError(f"validate_network_credential falhou: {resp.status_code} {resp.text}")
    return resp.json()
