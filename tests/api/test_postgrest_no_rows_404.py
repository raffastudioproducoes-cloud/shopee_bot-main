"""`.single()` sem linha (PGRST116, 0 rows) vira 404; outros erros do banco seguem 500."""
from fastapi import APIRouter
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from api.main import app

_router = APIRouter()


@_router.get("/__t/no-rows")
def _no_rows():
    raise APIError({"message": "m", "code": "PGRST116", "details": "The result contains 0 rows", "hint": None})


@_router.get("/__t/many-rows")
def _many_rows():
    raise APIError({"message": "m", "code": "PGRST116", "details": "The result contains 2 rows", "hint": None})


@_router.get("/__t/other")
def _other():
    raise APIError({"message": "boom", "code": "XX000", "details": None, "hint": None})


import pytest


@pytest.fixture(scope="module", autouse=True)
def _temporary_routes():
    """Rotas de teste existem só neste módulo; não poluem o app para os demais testes."""
    app.include_router(_router)
    yield
    app.router.routes[:] = [r for r in app.router.routes if not getattr(r, "path", "").startswith("/__t/")]
    app.openapi_schema = None


client = TestClient(app, raise_server_exceptions=False)


def test_zero_rows_is_404():
    r = client.get("/__t/no-rows")
    assert r.status_code == 404 and r.json() == {"detail": "Recurso não encontrado"}


def test_multiple_rows_stays_500():
    assert client.get("/__t/many-rows").status_code == 500


def test_other_database_error_stays_500_without_leaking_message():
    r = client.get("/__t/other")
    assert r.status_code == 500 and "boom" not in r.text
