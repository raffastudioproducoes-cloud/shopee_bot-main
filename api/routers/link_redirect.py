"""Redirecionador público de cliques: GET /r/{token} -> 302 para o link Shopee guardado.

Segurança: o destino vem SOMENTE do banco (nenhum parâmetro de URL é lido) e é
revalidado como HTTPS de host Shopee; token opaco de alta entropia; limite por IP
apenas em memória/Redis transitório. LGPD: nada de IP ou user agent é persistido;
só a contagem agregada por dia (post_link_click_days).
"""
import hashlib
import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..database import supabase
from ..rate_limiter import check_window
from ..shopee_affiliate_links import is_safe_shopee_link
from .auth import client_ip

logger = logging.getLogger(__name__)
router = APIRouter(tags=["redirect"], include_in_schema=False)

TOKEN = re.compile(r"[A-Za-z0-9_-]{22,64}")
RATE_ATTEMPTS = 60
RATE_WINDOW_SECONDS = 60
_RATE_STATE: dict = {}
# Pré-visualizações de link das redes não são cliques de pessoas: redireciona sem contar.
_PREVIEW_BOTS = re.compile(
    r"facebookexternalhit|facebot|meta-externalagent|twitterbot|slackbot|telegrambot|"
    r"whatsapp|linkedinbot|discordbot|googlebot|bingbot|crawler|spider",
    re.IGNORECASE,
)
_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow"}


def _not_found():
    raise HTTPException(status_code=404, detail="Link não encontrado")


def _lookup(token: str) -> str | None:
    row = (supabase.table("post_link_clicks").select("target_url")
           .eq("token", token).limit(1).execute()).data or []
    return row[0]["target_url"] if row else None


def _count(token: str) -> str | None:
    return supabase.rpc("record_post_link_click", {"p_token": token}).execute().data


@router.get("/r/{token}")
def follow(token: str, request: Request):
    if not TOKEN.fullmatch(token):
        _not_found()
    # Só o hash entra na chave do limitador; o IP em claro não é guardado.
    key = hashlib.sha256(client_ip(request).encode()).hexdigest()[:32]
    check_window("link_redirect", key, attempts=RATE_ATTEMPTS, window_seconds=RATE_WINDOW_SECONDS,
                 state=_RATE_STATE, detail="Muitos acessos. Tente novamente em instantes.")
    is_bot = bool(_PREVIEW_BOTS.search(request.headers.get("user-agent") or ""))
    try:
        target = _lookup(token) if is_bot else _count(token)
    except Exception:
        logger.warning("Redirecionador indisponível")
        raise HTTPException(status_code=503, detail="Link temporariamente indisponível")
    if not isinstance(target, str) or not is_safe_shopee_link(target):
        _not_found()
    return RedirectResponse(target, status_code=302, headers=_HEADERS)
