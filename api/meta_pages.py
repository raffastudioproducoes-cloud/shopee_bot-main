"""Fallback de Páginas concedidas via Login do Facebook para Empresas.

Em concessões novas (config_id) a Página pode pertencer a um Portfólio
Empresarial e /me/accounts volta vazio; as Páginas concedidas aparecem em
debug_token -> granular_scopes[].target_ids. Best-effort: qualquer falha
devolve [] (o chamador mantém o erro amigável). Nunca loga URL/token.
"""

import logging

import httpx

from apis.meta_version import GRAPH_URL, GRAPH_VERSION

logger = logging.getLogger("uvicorn.error")

_PAGE_SCOPES = {"pages_show_list", "pages_manage_posts", "pages_read_engagement"}
_FALLBACK_ERRORS = (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError)


def _granted_page_ids(debug_json: dict) -> list[str]:
    ids: set[str] = set()
    for scope in debug_json["data"]["granular_scopes"]:
        if scope.get("scope") in _PAGE_SCOPES:
            ids.update(str(i) for i in scope.get("target_ids") or [])
    return sorted(ids)


async def fetch_granted_pages(
    user_access_token: str, fields: str, app_id: str | None, secret: str | None
) -> list[dict]:
    """Páginas (dicts com `fields`) vindas de granular_scopes; [] se indisponível."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{GRAPH_URL}/{GRAPH_VERSION}/debug_token",
                params={"input_token": user_access_token},
                headers={"Authorization": f"Bearer {app_id}|{secret}"},
            )
            if res.status_code not in (200, 201):
                logger.warning("debug_token falhou: status=%s", res.status_code)
                return []
            pages = []
            for page_id in _granted_page_ids(res.json()):
                page_res = await client.get(
                    f"{GRAPH_URL}/{GRAPH_VERSION}/{page_id}",
                    params={"fields": fields},
                    headers={"Authorization": f"Bearer {user_access_token}"},
                )
                if page_res.status_code not in (200, 201):
                    logger.warning("Página concedida inacessível: status=%s", page_res.status_code)
                    continue
                pages.append(page_res.json())
            return pages
    except _FALLBACK_ERRORS as exc:
        logger.warning("Fallback debug_token falhou: error_type=%s", type(exc).__name__)
        return []
