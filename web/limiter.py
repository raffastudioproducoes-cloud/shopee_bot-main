import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Um unico storage Redis/Valkey por ambiente compartilha contadores entre
# workers/instancias. Em dev/testes, sem URI, conserva memory://.
# Se o Redis cair, a borda Flask degrada para limites locais (disponibilidade);
# os endpoints sensiveis do FastAPI falham fechados com 503.
_storage_uri = os.environ.get("RATELIMIT_STORAGE_URI", "").strip() or "memory://"
_key_prefix = os.environ.get("RATELIMIT_KEY_PREFIX", "auto-orbital:default")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=_storage_uri,
    key_prefix=f"{_key_prefix}:flask",
    in_memory_fallback_enabled=True,
)
