"""Pytest — ShopeeAutoVendas (API Python)

Testes de lógica básicos para validar a migração.
Rodar: pytest --noconftest tests/test_api.py
"""

import pytest
import os

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "test")
os.environ.setdefault("API_SECRET_KEY", "test-secret")


def test_auth_module_exists():
    """auth.py existe."""
    assert os.path.exists("api/routers/auth.py")


def test_main_py_imports():
    """main.py importa sem erro."""
    import api.main


def test_endpoints_auth_presentes():
    """Verifica que os endpoints /auth/* estão registrados."""
    from api.main import app

    paths = [route.path for route in app.routes if hasattr(route, "path")]

    assert "/auth/login" in paths, f"Falta /auth/login. paths={paths}"
    assert "/auth/logout" in paths, f"Falta /auth/logout. paths={paths}"
    assert "/auth/me" in paths, f"Falta /auth/me. paths={paths}"


def test_health_endpoint_presente():
    """Verifica que /health está registrado."""
    from api.main import app

    paths = [route.path for route in app.routes if hasattr(route, "path")]

    assert "/health" in paths, f"Falta /health. paths={paths}"
