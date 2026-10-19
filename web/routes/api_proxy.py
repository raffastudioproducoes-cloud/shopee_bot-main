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
from urllib.parse import urlparse

import requests
from flask import Blueprint, Response, request
from shopee_bot.web.helpers import cors_origins

API_INTERNAL_URL = os.environ.get("API_INTERNAL_URL", "http://127.0.0.1:8001")
_TIMEOUT = 30

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
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get("access_token"):
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
            timeout=_TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException:
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
