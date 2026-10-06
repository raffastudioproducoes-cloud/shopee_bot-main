"""
Override local do fixture autouse `_init_database` do conftest.py raiz.

O conftest raiz inicializa o Postgres do Flask (`shopee_bot.database.init`)
pra toda a suíte — mas os testes em tests/api/ exercitam só a API nova
(FastAPI), que fala com Supabase (mockado nos testes) e não com esse
Postgres. Reexecutar aqui evita exigir um Postgres local só pra rodar
estes testes.

O conftest raiz também roda `gevent.monkey.patch_all()` (necessário pro
Flask), o que trava o TestClient baseado em anyio/thread-portal usado
aqui. Por isso, rode estes testes com `--confcutdir` pra excluir o
conftest raiz da coleta:

    pytest --confcutdir=tests/api tests/api
"""

import os
import sys
import types

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

try:
    import shopee_bot  # noqa: F401
except ModuleNotFoundError:
    pkg = types.ModuleType("shopee_bot")
    pkg.__path__ = [PROJECT_ROOT]
    sys.modules["shopee_bot"] = pkg

import pytest

os.environ.setdefault(
    "APP_ENCRYPTION_KEY", "e7lc8f3AsY0VNg7Kpy1K5umJirUK6jwqkJg7_xhn0IY="
)


@pytest.fixture(scope="session", autouse=True)
def _init_database():
    yield


class FakeQueryBuilder:
    """Fake mínimo de query builder do Supabase que APLICA os filtros
    `.eq()` de verdade contra uma lista de linhas em memória — usado para
    provar isolamento entre perfis (não só que `.eq("profile_id", ...)` foi
    chamado, mas que o resultado realmente muda)."""

    def __init__(self, rows):
        self._rows = rows
        self._filters: dict = {}
        self._single = False

    def select(self, *_a, **_kw):
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def single(self):
        self._single = True
        return self

    def maybe_single(self):
        self._single = True
        return self

    def order(self, *_a, **_kw):
        return self

    def range(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def ilike(self, *_a, **_kw):
        return self

    def gte(self, *_a, **_kw):
        return self

    def lte(self, *_a, **_kw):
        return self

    def lt(self, *_a, **_kw):
        return self

    def execute(self):
        from unittest.mock import MagicMock

        matched = [
            row for row in self._rows
            if all(row.get(k) == v for k, v in self._filters.items())
        ]
        if self._single:
            return MagicMock(data=matched[0] if matched else None)
        return MagicMock(data=matched)


@pytest.fixture(autouse=True)
def _clear_rate_limit_state():
    """O rate limit em memória (api/routers/auth.py) é global de módulo;
    limpa entre testes pra não vazar contagem de um teste pro outro."""
    from api.routers import auth

    auth._login_attempts.clear()
    yield
    auth._login_attempts.clear()


@pytest.fixture
def real_profile_resolution():
    """Opt-in: testes que pedem este fixture exercitam a validação real de
    `profile_id` do token (api/routers/profiles.py::_resolve_profile_id)."""


@pytest.fixture(autouse=True)
def _stub_profile_resolution(request, monkeypatch):
    """Por padrão a validação de posse do `profile_id` do token (consulta ao
    Supabase) é neutralizada: os testes de products/lists só querem provar
    que o claim vira filtro, sem mockar a tabela `profiles`."""
    if "real_profile_resolution" in request.fixturenames:
        return
    from api.routers import profiles

    monkeypatch.setattr(profiles, "_resolve_profile_id", lambda pid, uid: pid)


@pytest.fixture
def fake_query_builder():
    return FakeQueryBuilder


@pytest.fixture
def old_token_without_profile_claim():
    """Cookie `access_token` no formato antigo (pré Task 5), sem `profile_id`
    no payload -- exercita o branch real de fallback, diferente de "sem
    cookie nenhum"."""
    from api.routers.auth import _create_token

    token = _create_token({"sub": "testuser", "id": 1})
    return {"access_token": token}


@pytest.fixture
def auth_headers_with_profile():
    """Cookie `access_token` cujo JWT carrega `profile_id` (Task 6).

    Gerado com a mesma `_create_token` de `api/routers/auth.py` (Task 5).
    `user_id`/`id` no payload é irrelevante nos testes que usam isso: eles
    autenticam via `app.dependency_overrides[get_current_user_id]` (padrão
    já usado em test_products.py/test_lists.py) -- só o claim `profile_id`
    é decodificado de verdade, por `get_current_profile_id`
    (api/routers/profiles.py), que lê o cookie direto sem tocar o Supabase.
    """
    from api.routers.auth import _create_token

    token = _create_token({"sub": "testuser", "id": 1, "profile_id": "profile-a"})
    return {"access_token": token}
