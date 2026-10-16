import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def test_postgres_dsn_password_is_not_in_sanitized_log():
    from api.utils.log_sanitizer import sanitize_log_data
    assert "senha-secreta" not in sanitize_log_data(
        "abrindo postgresql://user:senha-secreta@db.example/app"
    )


def test_request_id_is_echoed_and_invalid_ids_are_replaced():
    from api.main import app
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "pedido-123"})
        assert response.headers["X-Request-ID"] == "pedido-123"
        response = client.get("/health", headers={"X-Request-ID": "bad value!"})
        assert len(response.headers["X-Request-ID"]) > 0
        assert response.headers["X-Request-ID"] != "bad value!"


def test_ready_returns_503_when_database_is_unavailable(monkeypatch):
    from api import main
    monkeypatch.setattr(main, "get_supabase", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    with TestClient(main.app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503


def test_migration_lock_is_released(monkeypatch):
    from database import migrations
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    monkeypatch.setattr(migrations, "connect", lambda _: conn)
    migrations_dir = MagicMock()
    migrations_dir.glob.return_value = []
    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", migrations_dir)
    migrations.run_migrations()
    statements = [c.args[0] for c in conn.cursor.return_value.__enter__.return_value.execute.call_args_list]
    assert any("pg_try_advisory_lock" in statement for statement in statements)
    assert any("pg_advisory_unlock" in statement for statement in statements)


def test_dsn_with_at_and_slash_is_fully_masked():
    from api.utils.log_sanitizer import sanitize_log_data
    value = sanitize_log_data("postgresql://user:ab@cd/ef:gh@db.example/app")
    assert "ab@cd/ef:gh" not in value
    assert "***REDACTED***@db.example/app" in value
