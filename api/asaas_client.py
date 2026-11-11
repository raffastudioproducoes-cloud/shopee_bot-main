"""Cliente HTTP mínimo da API v3 do Asaas.

A chave vai só no header `access_token` e nunca aparece em log, erro ou
resposta. Sandbox e produção são escolhidos pela URL configurada.
"""
from __future__ import annotations

import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)
TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class AsaasUnavailable(RuntimeError):
    """Cobrança desligada (sem chave) ou Asaas fora do ar."""


class AsaasError(RuntimeError):
    """Asaas recusou a requisição; `messages` vem da resposta, sem dados sensíveis nossos."""

    def __init__(self, status: int, messages: list[str]):
        super().__init__(f"Asaas recusou ({status})")
        self.status, self.messages = status, messages


def environment() -> str:
    return "sandbox" if "sandbox" in (settings.asaas_api_url or "") else "production"


def enabled() -> bool:
    return bool(settings.asaas_api_key)


def may_bill(user_id: str | None) -> bool:
    """Produção cobra qualquer conta; sandbox só as contas de teste listadas."""
    if environment() == "production":
        return True
    testers = {t.strip() for t in (settings.asaas_sandbox_testers or "").split(",") if t.strip()}
    return bool(user_id) and str(user_id) in testers


def request(method: str, path: str, *, json: dict | None = None, params: dict | None = None,
            client: httpx.Client | None = None) -> dict:
    if not enabled():
        raise AsaasUnavailable("cobrança não configurada")
    headers = {
        "access_token": settings.asaas_api_key,
        "User-Agent": settings.asaas_user_agent,
        "Content-Type": "application/json",
    }
    url = settings.asaas_api_url.rstrip("/") + "/" + path.lstrip("/")
    own = client is None
    http = client or httpx.Client(timeout=TIMEOUT)
    try:
        resp = http.request(method, url, json=json, params=params, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("Asaas indisponível em %s %s: %s", method, path, type(exc).__name__)
        raise AsaasUnavailable("Asaas indisponível") from None
    finally:
        if own:
            http.close()
    if resp.status_code >= 500:
        logger.warning("Asaas respondeu %s em %s %s", resp.status_code, method, path)
        raise AsaasUnavailable("Asaas indisponível")
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        msgs = [str(e.get("description") or e.get("code") or "") for e in (data.get("errors") or [])]
        msgs = [m for m in msgs if m]
        logger.warning("Asaas recusou %s %s (%s): %s", method, path, resp.status_code, "; ".join(msgs[:3]) or "sem descrição")
        raise AsaasError(resp.status_code, msgs)
    return data


def create_customer(*, name: str, cpf_cnpj: str, email: str, mobile_phone: str | None,
                    external_reference: str, **kw) -> dict:
    body = {"name": name, "cpfCnpj": cpf_cnpj, "email": email,
            "externalReference": external_reference, "notificationDisabled": False}
    if mobile_phone:
        body["mobilePhone"] = mobile_phone
    return request("POST", "/customers", json=body, **kw)


def create_checkout(body: dict, **kw) -> dict:
    return request("POST", "/checkouts", json=body, **kw)


def create_pix_authorization(body: dict, **kw) -> dict:
    """Pix Automático (jornada 3): o QR Code inicial paga o 1º período e autoriza os próximos débitos."""
    return request("POST", "/pix/automatic/authorizations", json=body, **kw)


def get_pix_authorization(authorization_id: str, **kw) -> dict:
    return request("GET", f"/pix/automatic/authorizations/{authorization_id}", **kw)


def cancel_pix_authorization(authorization_id: str, **kw) -> dict:
    return request("DELETE", f"/pix/automatic/authorizations/{authorization_id}", **kw)


def checkout_url(checkout_id: str) -> str:
    """Formato documentado para produção; o host do sandbox ainda precisa ser
    confirmado no primeiro teste (a documentação só mostra asaas.com)."""
    host = "https://sandbox.asaas.com" if environment() == "sandbox" else "https://asaas.com"
    return f"{host}/checkoutSession/show?id={checkout_id}"
