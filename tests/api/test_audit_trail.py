"""Testes para api/audit_trail.py (auditoria imutável de alteração sensível,
item 10.3 do backlog) e sua instrumentação em endpoints de mutação."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import database as database_module
from api.audit_trail import record_audit_event
from api.main import app
from api.routers import products as products_router
from api.routers import product_media
from api.routers.auth import get_current_user_id


@pytest.fixture
def auth_client():
    """Cliente autenticado (user_id=42) com Supabase mockado."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    return TestClient(app)


def _mock_supabase(monkeypatch, execute_results):
    """Mocka `supabase.table(...)` encadeado, devolvendo `execute_results`
    em ordem a cada `.execute()`."""
    fake_client = MagicMock()
    query = fake_client.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.single.return_value = query
    query.update.return_value = query
    query.delete.return_value = query
    query.insert.return_value = query
    query.execute.side_effect = [MagicMock(data=d) for d in execute_results]
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    return fake_client, query


class TestRecordAuditEvent:
    """Unitário de record_audit_event: grava, sanitiza, nunca levanta."""

    def test_inserts_event_with_expected_fields(self, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        record_audit_event(
            entity="product",
            entity_id="1",
            user_id="42",
            action="product_price_changed",
            old_value={"price_min": 10.0},
            new_value={"price_min": 20.0},
        )

        fake_client.table.assert_called_once_with("audit_events")
        inserted = fake_client.table.return_value.insert.call_args[0][0]
        assert inserted["entity"] == "product"
        assert inserted["entity_id"] == "1"
        assert inserted["user_id"] == "42"
        assert inserted["action"] == "product_price_changed"
        assert inserted["old_value"] == {"price_min": 10.0}
        assert inserted["new_value"] == {"price_min": 20.0}
        fake_client.table.return_value.insert.return_value.execute.assert_called_once()

    def test_sanitizes_sensitive_keys_in_values(self, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        record_audit_event(
            entity="user",
            entity_id="7",
            user_id="1",
            action="user_deleted",
            old_value={"username": "joao", "password": "hunter2"},
            new_value=None,
        )

        inserted = fake_client.table.return_value.insert.call_args[0][0]
        assert inserted["old_value"]["username"] == "joao"
        assert inserted["old_value"]["password"] == "***REDACTED***"

    def test_does_not_raise_when_db_fails(self, monkeypatch):
        fake_client = MagicMock()
        fake_client.table.return_value.insert.return_value.execute.side_effect = Exception("db down")
        monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)

        record_audit_event(
            entity="product",
            entity_id="1",
            user_id="42",
            action="product_deleted",
            old_value={"id": 1},
            new_value=None,
        )  # não deve levantar


class TestProductMutationsTriggerAudit:
    """Preços importados são imutáveis; exclusão auditada após limpar mídia."""

    def test_price_change_is_rejected_and_not_audited(self, auth_client, monkeypatch):
        spy = MagicMock()
        monkeypatch.setattr(products_router, "record_audit_event", spy)
        res = auth_client.put("/products/1", json={"price_min": 15.0})
        assert res.status_code == 422
        spy.assert_not_called()

    def test_no_price_change_does_not_call_audit(self, auth_client, monkeypatch):
        spy = MagicMock()
        monkeypatch.setattr(products_router, "record_audit_event", spy)
        _mock_supabase(
            monkeypatch,
            [
                {"id": 1, "user_id": 42, "name": "Fone", "price_min": "10.0", "price_max": "20.0"},
                [{"id": 1, "user_id": 42, "name": "Novo nome", "price_min": "10.0", "price_max": "20.0"}],
            ],
        )

        res = auth_client.put("/products/1", json={"name": "Novo nome"})

        assert res.status_code == 200
        spy.assert_not_called()

    def test_delete_calls_audit(self, auth_client, monkeypatch):
        spy = MagicMock()
        monkeypatch.setattr(products_router, "record_audit_event", spy)
        media_cleanup = MagicMock()
        monkeypatch.setattr(product_media, "remove_product_media_files", media_cleanup)
        _mock_supabase(
            monkeypatch,
            [
                {"id": 1, "user_id": 42, "name": "Fone"},  # _get (before)
                [{"id": 1}],  # delete result
            ],
        )

        res = auth_client.delete("/products/1")

        assert res.status_code == 200
        media_cleanup.assert_called_once_with(42, 1)
        spy.assert_called_once()
        assert spy.call_args.kwargs["action"] == "product_deleted"
        assert spy.call_args.kwargs["entity"] == "product"
