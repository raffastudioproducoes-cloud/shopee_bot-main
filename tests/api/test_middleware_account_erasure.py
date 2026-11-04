"""Não ressuscitar dados identificáveis nos logs após exclusão integral."""
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import RequestLoggingMiddleware
from api import middleware as middleware_module


def _client(monkeypatch):
    monkeypatch.setattr(middleware_module.settings, "request_logging_enabled", True)
    spy = MagicMock()
    monkeypatch.setattr(RequestLoggingMiddleware, "_save", spy)
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.delete("/users/me")
    def own():
        return {"msg": "Conta removida"}

    @app.delete("/admin/users/00000000-0000-0000-0000-000000000001")
    def admin():
        return {"msg": "Usuário removido"}

    @app.post("/admin/users/00000000-0000-0000-0000-000000000001/erasure/retry")
    def retry():
        return {"msg": "Exclusão integral concluída"}

    @app.get("/visible")
    def visible():
        return {"ok": True}

    return TestClient(app), spy


def test_successful_account_erasure_creates_no_new_request_log(monkeypatch):
    client, save = _client(monkeypatch)
    with client:
        assert client.delete("/users/me").status_code == 200
        assert client.delete("/admin/users/00000000-0000-0000-0000-000000000001").status_code == 200
        assert client.post("/admin/users/00000000-0000-0000-0000-000000000001/erasure/retry").status_code == 200
    save.assert_not_called()


def test_other_request_still_logged(monkeypatch):
    client, save = _client(monkeypatch)
    with client:
        assert client.get("/visible").status_code == 200
    save.assert_called_once()
