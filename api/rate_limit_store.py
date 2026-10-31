"""Limites de autenticação compartilhados entre workers e instâncias.

Quando RATELIMIT_STORAGE_URI aponta para Redis/Valkey, a API usa operações
atômicas no mesmo armazenamento que o Flask-Limiter. Sem URL, mantém os
limites locais existentes (desenvolvimento e testes com um worker).
"""
from functools import lru_cache
import hashlib
import logging
import os
from uuid import uuid4

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

_UNAVAILABLE_DETAIL = "Proteção temporariamente indisponível. Tente novamente."
# Um script atômico evita aceitar mais tentativas que o teto quando N workers
# chegam ao mesmo tempo. O tempo é obtido do próprio servidor Redis.
_SLIDING_WINDOW_LUA = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
local window = tonumber(ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[2]) then
  redis.call('PEXPIRE', KEYS[1], window)
  return 0
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window)
return 1
"""


def _storage_uri() -> str:
    return os.environ.get("RATELIMIT_STORAGE_URI", "").strip()


def distributed_enabled() -> bool:
    """Habilitado apenas quando uma URI de armazenamento foi configurada."""
    return bool(_storage_uri() and _storage_uri() != "memory://")


@lru_cache(maxsize=4)
def _redis_for_url(url: str) -> Redis:
    if not url.startswith(("redis://", "rediss://")):
        raise ValueError("RATELIMIT_STORAGE_URI deve usar redis:// ou rediss://")
    return Redis.from_url(
        url,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
        decode_responses=True,
    )


def _key(kind: str, identity: str) -> str:
    prefix = os.environ.get("RATELIMIT_KEY_PREFIX", "auto-orbital:default")
    # Evita armazenar usernames e IPs em texto claro na chave Redis.
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"{prefix}:auth:{kind}:{digest}"


def _safe_call(action):
    try:
        return action()
    except (RedisError, OSError, ValueError, TimeoutError):
        # Nunca incluir a URI (potencialmente contém senha) nos logs.
        logger.warning("Armazenamento compartilhado de rate limit indisponível")
        raise HTTPException(status_code=503, detail=_UNAVAILABLE_DETAIL) from None


def allow_window(kind: str, identity: str, attempts: int, seconds: int) -> bool:
    """Janela deslizante atômica no Redis; chama somente se habilitado."""
    def run():
        client = _redis_for_url(_storage_uri())
        return int(client.eval(
            _SLIDING_WINDOW_LUA,
            1,
            _key(kind, identity),
            int(seconds * 1000),
            int(attempts),
            uuid4().hex,
        )) == 1

    return _safe_call(run)


def acquire_cooldown(kind: str, identity: str, seconds: int) -> bool:
    """Primeiro solicitante ganha o cooldown, replicado em todos os workers."""
    def run():
        client = _redis_for_url(_storage_uri())
        return bool(client.set(
            _key(kind, identity), "1", nx=True, px=int(seconds * 1000)
        ))

    return _safe_call(run)
