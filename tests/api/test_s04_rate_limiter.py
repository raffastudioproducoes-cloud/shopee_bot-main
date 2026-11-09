"""S-04: limite único, atômico com Redis, seguro sob concorrência e sem crescer sem limite sem Redis."""
import threading

import pytest
from fastapi import HTTPException

from api import rate_limit_store, rate_limiter
from api.routers import catalog, credentials, meta_callbacks


@pytest.fixture(autouse=True)
def _memory_mode(monkeypatch):
    monkeypatch.delenv("RATELIMIT_STORAGE_URI", raising=False)


def _hit(state, key="u1", attempts=3, window=60, **kw):
    rate_limiter.check_window("t", key, attempts=attempts, window_seconds=window,
                              state=state, detail="limite", **kw)


def test_allows_up_to_the_limit_then_429():
    state = {}
    for _ in range(3):
        _hit(state)
    with pytest.raises(HTTPException) as err:
        _hit(state)
    assert err.value.status_code == 429 and err.value.detail == "limite"


def test_window_expires_with_injected_clock():
    state, now = {}, [0.0]
    for _ in range(3):
        _hit(state, clock=lambda: now[0])
    now[0] = 61.0
    _hit(state, clock=lambda: now[0])  # a janela passou: libera de novo


def test_keys_are_independent():
    state = {}
    for _ in range(3):
        _hit(state, key="a")
    _hit(state, key="b")


def test_concurrent_calls_never_exceed_the_limit():
    """N chamadas simultâneas na mesma chave: no máximo `attempts` passam."""
    state, passed, blocked = {}, [], []
    barrier = threading.Barrier(50)

    def worker():
        barrier.wait()
        try:
            _hit(state, key="same", attempts=10)
            passed.append(1)
        except HTTPException:
            blocked.append(1)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(passed) == 10 and len(blocked) == 40


def test_memory_state_is_bounded_and_drops_oldest():
    state, now = {}, [0.0]
    for i in range(30):
        now[0] += 1
        _hit(state, key=f"k{i}", attempts=5, window=10_000, max_keys=10, clock=lambda: now[0])
    assert len(state) <= 10
    assert "k29" in state and "k0" not in state


def test_expired_keys_are_evicted_when_full():
    state, now = {}, [0.0]
    for i in range(10):
        _hit(state, key=f"old{i}", attempts=5, window=10, max_keys=10, clock=lambda: now[0])
    now[0] = 100.0
    _hit(state, key="new", attempts=5, window=10, max_keys=10, clock=lambda: now[0])
    assert set(state) == {"new"}


def test_distributed_mode_uses_atomic_store_and_ignores_local_state(monkeypatch):
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://redis.invalid:6379/0")
    calls = []

    def fake_allow(kind, identity, attempts, seconds):
        calls.append((kind, identity, attempts, seconds))
        return len(calls) <= 2

    monkeypatch.setattr(rate_limit_store, "allow_window", fake_allow)
    state = {}
    _hit(state, key="u9", attempts=2, window=30)
    _hit(state, key="u9", attempts=2, window=30)
    with pytest.raises(HTTPException) as err:
        _hit(state, key="u9", attempts=2, window=30)
    assert err.value.status_code == 429
    assert calls[0] == ("t", "u9", 2, 30)
    assert state == {}, "no modo distribuído nada fica em memória local"


def test_distributed_mode_fails_closed_with_503_when_redis_is_down(monkeypatch):
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://redis.invalid:6379/0")

    def broken(*_a, **_k):
        raise OSError("sem rede")

    monkeypatch.setattr(rate_limit_store, "_redis_for_url", broken)
    with pytest.raises(HTTPException) as err:
        _hit({}, key="u1")
    assert err.value.status_code == 503, "falha do armazenamento nega a operação, nunca libera"


@pytest.mark.parametrize("fn,args", [
    (catalog._check_search_rate_limit, (1,)),
    (credentials._check_test_rate_limit, (1,)),
])
def test_endpoints_use_the_shared_limiter(monkeypatch, fn, args):
    seen = []
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://redis.invalid:6379/0")
    monkeypatch.setattr(rate_limit_store, "allow_window",
                        lambda kind, identity, attempts, seconds: seen.append((kind, identity)) or True)
    fn(*args)
    assert seen and seen[0][1] == "1"


def test_meta_callback_limiter_is_shared_and_keeps_429_contract(monkeypatch):
    meta_callbacks._rate_attempts.clear()
    with pytest.raises(HTTPException) as err:
        for _ in range(5):
            meta_callbacks._check_memory_rate_limit("k", limit=3, window_seconds=60)
    assert err.value.status_code == 429
    meta_callbacks._rate_attempts.clear()


def test_describe_mode_never_leaks_the_uri(monkeypatch):
    secret = "redis://user:SENHA-SECRETA@host.invalid:6379/0"
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", secret)

    def down(*_a, **_k):
        raise OSError("falhou " + secret)

    monkeypatch.setattr(rate_limit_store, "_redis_for_url", down)
    level, message = rate_limit_store.describe_mode(1)
    assert level == "warning" and "SENHA-SECRETA" not in message and "host.invalid" not in message


def test_describe_mode_reports_memory_and_multiworker_warning(monkeypatch):
    assert rate_limit_store.describe_mode(1)[0] == "info"
    level, message = rate_limit_store.describe_mode(3)
    assert level == "warning" and "3 workers" in message


def test_describe_mode_reports_healthy_distributed(monkeypatch):
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://redis.invalid:6379/0")
    monkeypatch.setattr(rate_limit_store, "ping", lambda: True)
    assert rate_limit_store.describe_mode(1)[0] == "info"
