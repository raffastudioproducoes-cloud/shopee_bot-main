"""Testes do middleware de histórico de requisições (api/middleware.py).

Ponto crítico: por padrão (`request_logging_enabled=False`) o middleware não
pode tocar em `get_supabase()` de jeito nenhum — testes de outros routers
mockam `get_supabase()` com uma fila de `execute.side_effect` que já é
consumida na ordem exata que o próprio endpoint espera; um insert extra do
middleware nessa mesma fila desincronizaria todos eles silenciosamente.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import middleware as middleware_module
from api.config import settings
from api.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _restore_flag():
    original = settings.request_logging_enabled
    yield
    settings.request_logging_enabled = original


class TestDisabledByDefault:
    def test_never_calls_get_supabase_when_disabled(self, monkeypatch, client):
        settings.request_logging_enabled = False

        def _boom():
            raise AssertionError(
                "middleware não deveria chamar get_supabase() com o flag desligado"
            )

        monkeypatch.setattr(middleware_module, "get_supabase", _boom)

        res = client.get("/health")

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestEnabled:
    def test_logs_method_path_and_status(self, monkeypatch, client):
        settings.request_logging_enabled = True

        fake_client = MagicMock()
        table = fake_client.table.return_value
        table.insert.return_value = table
        monkeypatch.setattr(middleware_module, "get_supabase", lambda: fake_client)

        # /health fica fora do log (_SKIP_PATHS) por ser só um ping de
        # infra — uma rota real (mesmo sem sessão) exercita o caminho normal.
        res = client.get("/credentials")

        assert res.status_code == 401
        fake_client.table.assert_called_with("request_logs")
        inserted = table.insert.call_args[0][0]
        assert inserted["method"] == "GET"
        assert inserted["path"] == "/credentials"
        assert inserted["status_code"] == 401
        assert inserted["user_id"] is None
        assert inserted["username"] is None

    def test_logging_failure_does_not_break_the_real_response(
        self, monkeypatch, client
    ):
        settings.request_logging_enabled = True
        monkeypatch.setattr(
            middleware_module,
            "get_supabase",
            lambda: (_ for _ in ()).throw(RuntimeError("supabase fora do ar")),
        )

        res = client.get("/health")

        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_unauthenticated_401_is_still_logged(self, monkeypatch, client):
        settings.request_logging_enabled = True

        fake_client = MagicMock()
        table = fake_client.table.return_value
        table.insert.return_value = table
        monkeypatch.setattr(middleware_module, "get_supabase", lambda: fake_client)

        res = client.get("/credentials")

        assert res.status_code == 401
        inserted = table.insert.call_args[0][0]
        assert inserted["path"] == "/credentials"
        assert inserted["status_code"] == 401
