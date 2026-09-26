"""
Database module for the new API Python (FastAPI).

Provides Supabase client connection for the migrated API.
Coexists with Flask during migration.
"""

from functools import lru_cache

from supabase import create_client, Client

from .config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Returns cached Supabase client instance."""
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be configured"
        )
    return create_client(settings.supabase_url, settings.supabase_key)


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
