"""Fixtures compartilhadas de teste.

Roda contra um Postgres local isolado (não a instância Supabase de
produção) — configurar POSTGRES_HOST/USER/PASSWORD/DB antes de rodar
`pytest`, ou usar os defaults abaixo (localhost:5433, usuário/senha/db
"dev", igual ao Postgres portátil usado nas sessões de teste manual).

O nome real da pasta do projeto é "shopee_bot-main", não "shopee_bot"
— em produção (Docker) o WORKDIR é literalmente /shopee_bot, então o
pacote "shopee_bot.*" resolve nativamente. Aqui registramos um alias
de pacote pra funcionar também fora do Docker.
"""
# fmt: off
# gevent precisa fazer o monkey-patch antes de qualquer outro import
# tocar em socket/threading — senão trava (mistura primitivas
# patcheadas com não-patcheadas). Import de shopee_bot.web faz isso
# tarde demais quando pytest já iniciou suas próprias threads.
from gevent import monkey
monkey.patch_all()
# fmt: on

import os
import sys
import types
import secrets

import pytest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

try:
    import shopee_bot  # noqa: F401
except ModuleNotFoundError:
    pkg = types.ModuleType("shopee_bot")
    pkg.__path__ = [PROJECT_ROOT]
    sys.modules["shopee_bot"] = pkg

os.environ.setdefault("POSTGRES_HOST", "localhost:5433")
os.environ.setdefault("POSTGRES_USER", "dev")
os.environ.setdefault("POSTGRES_PASSWORD", "dev")
os.environ.setdefault("POSTGRES_DB", "dev")
os.environ.setdefault("FLASK_SESSION_SECRET", "test_only_secret")
os.environ.setdefault(
    "FLASK_UPLOAD_FOLDER", os.path.join(PROJECT_ROOT, "upload")
)
os.environ.setdefault("FLASK_MAX_CONTENT_LENGTH", "52428800")
os.environ.setdefault("LOG_LEVEL", "30")
os.environ.setdefault("THREADS_PERMISSIONS", "")
os.environ.setdefault(
    "APP_ENCRYPTION_KEY", "e7lc8f3AsY0VNg7Kpy1K5umJirUK6jwqkJg7_xhn0IY="
)

from shopee_bot.database import init as init_db, get_conn, put_conn  # noqa: E402
from shopee_bot.database import users, shopee_credentials, \
    threads_credentials  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_database():
    init_db()


@pytest.fixture(scope="session")
def app():
    from shopee_bot.web import app as flask_app
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_user():
    """Cria um usuário descartável no banco de teste. Não limpa depois
    — é banco local isolado, resetável a qualquer momento."""
    username = f"test_{secrets.token_hex(4)}"
    password = "TestPass123"

    conn = get_conn()
    with conn.transaction():
        user_id = users.insert(
            {"username": username, "password": password, "access": "USER"},
            conn
        )
        shopee_credentials.insert(
            user_id,
            {"app_id": None, "secret": None, "status": False},
            conn
        )
        threads_credentials.insert(
            user_id,
            {"t_user_id": None, "access_token": None, "status": False},
            conn
        )
    put_conn(conn)

    return {"id": user_id, "username": username, "password": password}
