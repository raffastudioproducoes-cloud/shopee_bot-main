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
