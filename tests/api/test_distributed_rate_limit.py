"""Contrato do rate limiter distribuído sem depender de rede real.

Os workers independentes usam a mesma chave Redis para cada identidade.
"""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from api import rate_limit_store
from api.main import app
from api.routers import auth as auth_module


@pytest.fixture(autouse=True)
def _distributed_storage(monkeypatch):
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://rate-limit.invalid:6379/0")
    monkeypatch.setenv("RATELIMIT_KEY_PREFIX", "test:auto-orbital")


def test_distributed_auth_login_blocks_after_five_attempts(monkeypatch):
    shared = {"attempts": 0}

    def eval_script(script, numkeys, key, window, limit, nonce):
        assert "ZREMRANGEBYSCORE" in script
        assert numkeys == 1
        assert window == 60000
        assert limit == 5
        assert "test:auto-orbital:auth:login:" in key
        shared["attempts"] += 1
        return int(shared["attempts"] <= limit)

    client = MagicMock()
    client.eval.side_effect = eval_script
    monkeypatch.setattr(rate_limit_store, "_redis_for_url", lambda _: client)

    for _ in range(5):
        auth_module._check_login_rate_limit("login:shared-user")

    with pytest.raises(HTTPException) as blocked:
        auth_module._check_login_rate_limit("login:shared-user")
    assert blocked.value.status_code == 429
    assert client.eval.call_count == 6
    assert "shared-user" not in str(client.eval.call_args)


def test_cooldown_shared_between_independent_calls(monkeypatch):
    shared_keys = set()
    client = MagicMock()

    def set_if_absent(key, value, *, nx, px):
        assert nx is True
        assert px == 30000
        if key in shared_keys:
            return None
        shared_keys.add(key)
        return True

    client.set.side_effect = set_if_absent
    monkeypatch.setattr(rate_limit_store, "_redis_for_url", lambda _: client)

    assert rate_limit_store.acquire_cooldown("register", "198.51.100.10", 30)
    assert not rate_limit_store.acquire_cooldown("register", "198.51.100.10", 30)
    assert rate_limit_store.acquire_cooldown("register", "198.51.100.11", 30)


def test_redis_outage_fails_closed_without_exposing_uri(monkeypatch):
    client = MagicMock()
    client.eval.side_effect = RedisConnectionError("secret-internal-url")
    monkeypatch.setattr(rate_limit_store, "_redis_for_url", lambda _: client)

    with pytest.raises(HTTPException) as blocked:
        rate_limit_store.allow_window("login", "anyone", 5, 60)
    assert blocked.value.status_code == 503
    assert "secret" not in blocked.value.detail


def test_reset_endpoint_uses_distributed_cooldown_before_database(monkeypatch):
    monkeypatch.setattr(rate_limit_store, "acquire_cooldown", lambda *args: False)
    monkeypatch.setattr(auth_module, "_get_user_from_supabase", lambda *args: pytest.fail("DB nao deve ser consultado"))
    with TestClient(app) as browser:
        response = browser.post("/auth/reset-password", json={
            "username": "anyone",
            "current_password": "old-password",
            "new_password": "new-password-123",
        })
    assert response.status_code == 429


def test_login_endpoint_returns_503_when_redis_is_offline(monkeypatch):
    client = MagicMock()
    client.eval.side_effect = RedisConnectionError("unreachable")
    monkeypatch.setattr(rate_limit_store, "_redis_for_url", lambda _: client)
    monkeypatch.setattr(auth_module, "_get_user_from_supabase", lambda *args: pytest.fail("DB nao deve ser consultado"))
    with TestClient(app) as browser:
        response = browser.post("/auth/login", data={"username": "anyone", "password": "somepass"})
    assert response.status_code == 503
