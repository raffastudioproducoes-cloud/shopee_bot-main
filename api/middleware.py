"""
Middleware de log de requisições — histórico de toda chamada à API nova
(método, path, status, duração, usuário, erro/redirect) gravado na tabela
`request_logs`.

Existe pra debug remoto: quando algo falha em produção (ex: callback OAuth
de uma rede social), dá pra consultar esse histórico direto no Supabase em
vez de pedir print/log de cada erro pro usuário.

Desligado por padrão (`settings.request_logging_enabled = False`) — nos
testes isso evita que toda requisição da suíte dispare um insert extra na
tabela mockada de `get_supabase()`, o que desincronizaria as sequências de
`execute.side_effect` que os testes de outros routers já dependem. Em
produção é ligado via env var `REQUEST_LOGGING_ENABLED=true`.
"""

import logging
import contextvars
import re
import uuid
import time

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .config import settings
from .database import get_supabase
from .routers.auth import client_ip
from .utils.log_sanitizer import sanitize_log_data

logger = logging.getLogger("uvicorn.error")

_MAX_TEXT_LEN = 2000
_SKIP_PATHS = {"/health", "/health/ready"}
request_id_context = contextvars.ContextVar("request_id", default=None)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")

class AccessLogRedactor(logging.Filter):
    """Mascara `?code=`/`state=`/tokens na URL do access log do uvicorn
    (ex: codigo de confirmacao de exclusao de dados, que viaja em query string)."""

    def filter(self, record):
        if isinstance(record.args, tuple):
            record.args = tuple(
                sanitize_log_data(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        return True


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get() or "-"
        return True

logger.addFilter(RequestIDFilter())

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        candidate = request.headers.get("X-Request-ID", "")
        request_id = candidate if _REQUEST_ID_RE.fullmatch(candidate) else uuid.uuid4().hex
        token = request_id_context.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            return response
        finally:
            request_id_context.reset(token)


def _user_from_cookie(request: Request) -> tuple[str | None, str | None, str | None]:
    """Decodifica o JWT do cookie sem bater no banco — best-effort, nunca
    levanta exceção (log não pode derrubar a requisição real nem depender
    de uma segunda ida ao Supabase). Devolve (id, username, profile_id); o
    `profile_id` é só o claim do token (não validado — é rótulo de log)."""
    token = request.cookies.get("access_token")
    if not token:
        return None, None, None
    try:
        decoded = jwt.decode_complete(
            token, settings.api_secret_key, algorithms=["HS256"]
        )
        header = decoded.get("header") or {}
        if "crit" in header:
            # RFC 7515 §4.1.11 / GHSA-752w-5fwx-jx9f: nenhuma extensão crítica é suportada
            return None, None, None
        payload = decoded.get("payload") or {}
    except Exception:
        return None, None, None
    return payload.get("id"), payload.get("sub"), payload.get("profile_id")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.request_logging_enabled or request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        user_id, username, profile_id = _user_from_cookie(request)
        status_code = 500
        error = None
        redirect_to = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            location = response.headers.get("location")
            if location:
                # Callbacks OAuth (instagram/x/tiktok) sempre redirecionam com
                # 307 e colocam o resultado real (?error=... ou sucesso) na
                # query string do redirect, não no status code.
                redirect_to = location
            return response
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            # Se o DELETE integral terminou, não recriar dados pessoais no
            # request_logs depois de a transação final ter feito o expurgo.
            # Também não persistir o UUID do alvo no path de DELETE admin.
            path = request.url.path
            erasure_completed = status_code == 200 and (
                (request.method == "DELETE" and path == "/users/me")
                or (request.method == "DELETE" and re.fullmatch(
                    r"/admin/users/[0-9a-fA-F-]{36}", path
                ))
                or (request.method == "POST" and re.fullmatch(
                    r"/admin/users/[0-9a-fA-F-]{36}/erasure/retry", path
                ))
            )
            if erasure_completed:
                return
            self._save(
                request, user_id, username, status_code, duration_ms, error, redirect_to,
                profile_id,
            )

    def _save(
        self, request, user_id, username, status_code, duration_ms, error, redirect_to,
        profile_id=None,
    ):
        try:
            # Centraliza a defesa: qualquer chamador de _save, inclusive testes
            # e futuros middlewares, grava somente uma versao segura do contexto.
            safe_error = sanitize_log_data(error)[:_MAX_TEXT_LEN] if error else None
            safe_redirect_to = (
                sanitize_log_data(redirect_to)[:_MAX_TEXT_LEN] if redirect_to else None
            )
            supabase = get_supabase()
            supabase.table("request_logs").insert(
                {
                    "user_id": user_id,
                    "username": username,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "error": safe_error,
                    "redirect_to": safe_redirect_to,
                    "client_ip": client_ip(request) if request.client else None,
                    **({"profile_id": profile_id} if profile_id else {}),
                }
            ).execute()
        except Exception:
            # Log é auxiliar, nunca pode derrubar ou mascarar a resposta real.
            logger.warning("Falha ao gravar request_log (não crítico)", exc_info=True)
