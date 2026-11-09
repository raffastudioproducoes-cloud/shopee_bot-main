"""Janela deslizante única para os limites por usuário/IP da API (achado S-04).

Antes havia implementações separadas (catálogo, teste de credenciais, callbacks Meta) que
eram sempre em memória e, em dois casos, nunca descartavam chaves. Agora todas passam por
aqui:

- Com `RATELIMIT_STORAGE_URI` (Redis/Valkey): contagem ATÔMICA e compartilhada entre workers
  e instâncias (`rate_limit_store.allow_window`); se o Redis falhar a operação é negada com
  503 (fail-closed), nunca liberada.
- Sem Redis: janela em memória protegida por trava (N chamadas concorrentes não passam do
  teto) e com número máximo de chaves, para o dicionário não crescer sem limite. Só é
  correto com UMA instância; o log de inicialização informa o modo ativo.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Hashable

from fastapi import HTTPException

from . import rate_limit_store

DEFAULT_MAX_KEYS = 10_000
_LOCK = threading.Lock()


def _evict(state: dict, now: float, window_seconds: float, max_keys: int) -> None:
    if len(state) <= max_keys:
        return
    for key in [k for k, stamps in state.items() if not stamps or now - stamps[-1] >= window_seconds]:
        del state[key]
    while len(state) > max_keys:  # ainda cheio: descarta a chave mais antiga
        del state[min(state, key=lambda k: state[k][-1])]


def check_window(
    kind: str,
    key: Hashable,
    *,
    attempts: int,
    window_seconds: int,
    state: dict,
    detail: str,
    max_keys: int = DEFAULT_MAX_KEYS,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Registra uma tentativa; responde 429 com `detail` se o teto da janela foi atingido."""
    if rate_limit_store.distributed_enabled():
        if not rate_limit_store.allow_window(kind, str(key), attempts, window_seconds):
            raise HTTPException(status_code=429, detail=detail)
        return

    now = clock()
    with _LOCK:
        recent = [t for t in state.get(key, ()) if now - t < window_seconds]
        if len(recent) >= attempts:
            state[key] = recent
            raise HTTPException(status_code=429, detail=detail)
        recent.append(now)
        state[key] = recent
        _evict(state, now, window_seconds, max_keys)
