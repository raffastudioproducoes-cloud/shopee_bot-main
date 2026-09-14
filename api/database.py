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


def supabase() -> Client:
    """Delegated Supabase client — calls get_supabase() once.

    This is the function routers should import and use.
    """
    return get_supabase()
