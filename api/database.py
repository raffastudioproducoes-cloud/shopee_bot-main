"""
Database module for the new API Python (FastAPI).

Provides Supabase client connection for the migrated API.
Coexists with Flask during migration.
"""

import logging
import time
from functools import lru_cache

import httpx
from supabase import create_client, Client

from .config import settings


logger = logging.getLogger(__name__)

_IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}


def harden_http_session(session: httpx.Client) -> httpx.Client:
    """Repete UMA vez a chamada quando a conexão compartilhada com o PostgREST morreu.

    A conexão HTTP/2 fica aberta entre as requisições. Quando o servidor a fecha (ociosidade,
    instância do Render que dormiu e acordou), a primeira escrita falha com `Broken pipe` e a rota
    inteira respondia 500; com chamadas simultâneas, todas falhavam juntas.
    - `WriteError`/`ConnectError`: o pedido nem saiu da máquina, então repetir é seguro para qualquer método.
    - `ReadError`/`RemoteProtocolError`: o servidor pode ter processado; só repete leituras (GET/HEAD).
    O httpcore descarta a conexão quebrada, então a repetição abre uma conexão nova.
    """
    original_send = session.send

    def send(request: httpx.Request, *args, **kwargs):
        try:
            return original_send(request, *args, **kwargs)
        except (httpx.WriteError, httpx.ConnectError) as first:
            error = first
        except (httpx.ReadError, httpx.RemoteProtocolError) as first:
            if request.method not in _IDEMPOTENT_METHODS:
                raise
            error = first
        logger.warning("Conexão com o banco falhou (%s); uma nova tentativa", type(error).__name__)
        time.sleep(0.05)
        return original_send(request, *args, **kwargs)

    session.send = send  # type: ignore[method-assign]
    return session


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Returns cached Supabase client instance."""
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be configured"
        )
    client = create_client(settings.supabase_url, settings.supabase_key)
    harden_http_session(client.postgrest.session)
    return client


def init_db() -> None:
    """Initialize database connection (called at app startup)."""
    get_supabase()


class _SupabaseProxy:
    """Lazy proxy that behaves like a `Client` instance.

    Routers do `from ..database import supabase` then call
    `supabase.table(...)` directly (not `supabase().table(...)`), so
    `supabase` must be an object, not a function. `__getattr__` forwards
    every attribute access to `get_supabase()`, which keeps the existing
    `lru_cache` singleton semantics (client built once, reused after).
    """

    def __getattr__(self, name: str):
        return getattr(get_supabase(), name)


supabase = _SupabaseProxy()
