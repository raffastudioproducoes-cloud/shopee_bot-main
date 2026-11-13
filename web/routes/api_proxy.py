"""
Proxy transparente /api/* -> FastAPI interno (api/main.py).

Por quê: no Render (e no Docker), só o Flask escuta a porta pública.
O FastAPI novo sobe como processo uvicorn interno em 127.0.0.1:8001
(ver gunicorn.conf.py::on_starting). Esta rota é o pipe que repassa
tráfego externo pra ele — igual em espírito a web/routes/internal.py,
mas na direção oposta (lá é FastAPI->Flask via segredo; aqui é
browser->Flask->FastAPI, sem segredo, porque o FastAPI tem seu próprio
JWT/cookie de sessão e não usa Flask-WTF).
"""

import os
import re
from urllib.parse import urlparse

import requests
from flask import Blueprint, Response, current_app, request
from shopee_bot.web.helpers import cors_origins

API_INTERNAL_URL = os.environ.get("API_INTERNAL_URL", "http://127.0.0.1:8001")
_TIMEOUT = 30
# A transcodificação segura pode levar até 90 s, além de ffprobe e Storage.
# Este prazo maior vale SOMENTE para upload da galeria de Produtos.
_PRODUCT_MEDIA_TIMEOUT = (5, 180)  # conexão, leitura/resposta do FastAPI
# A ativação de campanha valida cotas, baixa/copia mídias e testa OAuth por
# rede; com muitas ocorrências passa de 30 s. Prazo maior SOMENTE para ela,
# abaixo do limite de borda do Render. A operação é idempotente por rascunho.
_CAMPAIGN_ACTIVATE_TIMEOUT = (5, 90)
_CAMPAIGN_ACTIVATE_PATH = re.compile(r"campaigns/drafts/[0-9A-Za-z-]+/activate")

# headers que não devem ser repassados 1:1 entre Flask e o FastAPI
# interno — hop-by-hop ou recalculados pelo lado que recebe
# x-forwarded-for: o valor vindo do browser é forjável; é substituído
# abaixo pelo IP já resolvido pelo ProxyFix (web/__init__.py), que o
# FastAPI usa como IP real nos rate limits (api/routers/auth.py::client_ip).
_REQUEST_HEADERS_TO_DROP = {"host", "content-length", "x-forwarded-for"}
_RESPONSE_HEADERS_TO_DROP = {
    "content-encoding", "content-length", "transfer-encoding", "connection",
}

api_proxy_bp = Blueprint("api_proxy", __name__, url_prefix="/api")


@api_proxy_bp.route(
    "/<path:subpath>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
def proxy(subpath):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (request.cookies.get("access_token") or request.cookies.get("sb_google_pending")):
        source = request.headers.get("Origin") or request.headers.get("Referer")
        parsed = urlparse(source or "")
        allowed = {request.host_url, *cors_origins()}
        if not source or not any(
            (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc)
            for origin in map(urlparse, allowed)
        ):
            return {"error": "Origem da requisição inválida"}, 403
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _REQUEST_HEADERS_TO_DROP
    }
    if request.remote_addr:
        headers["X-Forwarded-For"] = request.remote_addr
    is_product_media_upload = request.method == "POST" and bool(
        re.fullmatch(r"products/\d+/media", subpath)
    )
    is_campaign_activation = request.method == "POST" and bool(
        _CAMPAIGN_ACTIVATE_PATH.fullmatch(subpath)
    )
    if is_product_media_upload:
        upstream_timeout = _PRODUCT_MEDIA_TIMEOUT
    elif is_campaign_activation:
        upstream_timeout = _CAMPAIGN_ACTIVATE_TIMEOUT
    else:
        upstream_timeout = _TIMEOUT
    try:
        # ponytail: get_data() carrega o corpo inteiro em memória; ok
        # porque Flask já limita isso via MAX_CONTENT_LENGTH (mesmo
        # teto de qualquer outra rota do app). Trocar por stream real
        # (request.stream) se um dia precisar de upload maior que isso.
        upstream = requests.request(
            method=request.method,
            url=f"{API_INTERNAL_URL}/{subpath}",
            params=request.args,
            headers=headers,
            data=request.get_data(),
            timeout=upstream_timeout,
            allow_redirects=False,
        )
    except requests.Timeout:
        current_app.logger.warning(
            "Timeout no proxy interno: escopo=%s",
            "product-media-upload" if is_product_media_upload
            else "campaign-activation" if is_campaign_activation else "api-general",
        )
        if is_campaign_activation:
            return {
                "error": (
                    "A ativação demorou além do limite de resposta. Ela pode ter "
                    "terminado no servidor: confira a seção 06 antes de tentar de novo."
                )
            }, 504
        if is_product_media_upload:
            return {
                "error": (
                    "O processamento da mídia demorou além do limite de resposta. "
                    "Confira a galeria do produto antes de reenviar o arquivo."
                )
            }, 504
        return {"error": "API interna não respondeu a tempo"}, 504
    except requests.RequestException:
        current_app.logger.warning(
            "Falha de conexão no proxy interno: escopo=%s",
            "product-media-upload" if is_product_media_upload else "api-general",
        )
        return {"error": "API interna indisponível"}, 502

    response_headers = [
        (k, v) for k, v in upstream.raw.headers.items()
        if k.lower() not in _RESPONSE_HEADERS_TO_DROP
    ]
    return Response(
        upstream.content,
        status=upstream.status_code,
        headers=response_headers,
    )


# Redirecionador público de cliques (api/routers/link_redirect.py). Só GET e só o
# formato do token; o destino vem do banco no FastAPI, nunca desta URL.
click_redirect_bp = Blueprint("click_redirect", __name__)


@click_redirect_bp.get("/r/<token>")
def click_redirect(token):
    if not re.fullmatch(r"[A-Za-z0-9_-]{22,64}", token):
        return {"error": "Link não encontrado"}, 404
    return proxy(f"r/{token}")
