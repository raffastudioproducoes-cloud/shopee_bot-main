"""
Serve o build do frontend React (frontend/dist) como SPA.

Registrado por último em web/__init__.py de propósito: o catch-all abaixo é
o fallback final e nunca deve sobrepor uma rota Flask já registrada (Jinja
legado sob LEGACY_PANEL_ENABLED, /panel, /auth, /internal, /api, /static,
/media, /health, /product-lists, /garimpo, /startup) — Werkzeug prioriza
rotas estáticas/mais específicas sobre a rota com <path:...> independente
da ordem de registro, e o prefixo abaixo é só uma trava extra de segurança.

Quando LEGACY_PANEL_ENABLED=false (default), index()/products_bp/
users_bp não são registrados (ver web/__init__.py) e este catch-all assume
"/", "/products", "/posts", "/users" — servindo o index.html do React, que
resolve a rota via client-side routing (frontend/src/router.tsx).
"""

from pathlib import Path

from flask import Blueprint, abort, request, send_from_directory

spa_bp = Blueprint("spa", __name__)


@spa_bp.after_request
def _staging_noindex(response):
    """Keep staging SPA previews out of search indexes before JS executes."""
    hostname = request.host.partition(":")[0].lower()
    if hostname.endswith("-staging.onrender.com") and response.mimetype == "text/html":
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _html_or_worker_response(directory: Path, filename: str):
    """Do not cache SPA navigations or sw.js across production releases."""
    response = send_from_directory(directory, filename)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# repo_root/frontend/dist — ver Dockerfile (estágio frontend-build copia o
# resultado de `npm run build` pra cá antes do estágio Python final)
_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_ASSETS_DIR = _DIST_DIR / "assets"

# paths servidos por outras rotas Flask — o catch-all nunca deve responder
# por eles, mesmo que a rota real não esteja registrada no momento
_RESERVED_PREFIXES = ("api/", "static/", "panel/", "auth/", "internal/")


# Arquivos com hash no nome (assets/) nunca mudam; vídeos, marcas e ícones de public/ mudam raramente.
_IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
_PUBLIC_FILE_CACHE = "public, max-age=86400"


@spa_bp.get("/assets/<path:filename>")
def spa_assets(filename):
    if not _ASSETS_DIR.is_dir():
        abort(404)
    response = send_from_directory(_ASSETS_DIR, filename)
    # O Vite grava o hash do conteúdo no nome do arquivo: cada versão tem nome novo, então o
    # navegador pode guardar por 1 ano sem perguntar de novo (menos uma requisição por arquivo).
    response.headers["Cache-Control"] = _IMMUTABLE_CACHE
    return response


@spa_bp.get("/", defaults={"path": ""})
@spa_bp.get("/<path:path>")
def spa_catch_all(path):
    if path.startswith(_RESERVED_PREFIXES):
        abort(404)

    # Vite copia frontend/public/* pra raiz de frontend/dist/ (vídeos,
    # favicon, robots.txt, etc.) — sem essa checagem, qualquer arquivo
    # ali fora de /assets/ cai no fallback de index.html abaixo e é
    # servido com Content-Type text/html em vez do arquivo real.
    if path and path != "index.html" and (_DIST_DIR / path).is_file():
        if path == "sw.js":
            return _html_or_worker_response(_DIST_DIR, path)
        response = send_from_directory(_DIST_DIR, path)
        response.headers["Cache-Control"] = _PUBLIC_FILE_CACHE
        return response

    index_file = _DIST_DIR / "index.html"
    if not index_file.is_file():
        # frontend não buildado (dev sem `npm run build`) — não mascarar
        # com um 404 silencioso enganoso, mas também não quebrar rotas
        # Flask que ainda não foram registradas
        abort(404)

    return _html_or_worker_response(_DIST_DIR, "index.html")
