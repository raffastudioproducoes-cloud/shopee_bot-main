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
import time

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .config import settings
from .database import get_supabase
from .routers.auth import client_ip

logger = logging.getLogger("uvicorn.error")

_MAX_TEXT_LEN = 2000
_SKIP_PATHS = {"/health"}


def _user_from_cookie(request: Request) -> tuple[str | None, str | None, str | None]:
    """Decodifica o JWT do cookie sem bater no banco — best-effort, nunca
    levanta exceção (log não pode derrubar a requisição real nem depender
    de uma segunda ida ao Supabase). Devolve (id, username, profile_id); o
    `profile_id` é só o claim do token (não validado — é rótulo de log)."""
    token = request.cookies.get("access_token")
    if not token:
        return None, None, None
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=["HS256"])
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
                redirect_to = location[:_MAX_TEXT_LEN]
            return response
        except Exception as exc:
            error = str(exc)[:_MAX_TEXT_LEN]
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._save(
                request, user_id, username, status_code, duration_ms, error, redirect_to,
                profile_id,
            )

    def _save(
        self, request, user_id, username, status_code, duration_ms, error, redirect_to,
        profile_id=None,
    ):
        try:
            supabase = get_supabase()
            supabase.table("request_logs").insert(
                {
                    "user_id": user_id,
                    "username": username,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "error": error,
                    "redirect_to": redirect_to,
                    "client_ip": client_ip(request) if request.client else None,
                    **({"profile_id": profile_id} if profile_id else {}),
                }
            ).execute()
        except Exception:
            # Log é auxiliar, nunca pode derrubar ou mascarar a resposta real.
            logger.warning("Falha ao gravar request_log (não crítico)", exc_info=True)
