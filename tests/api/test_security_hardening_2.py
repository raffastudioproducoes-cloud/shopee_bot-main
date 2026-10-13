"""Auditoria de segurança (lote 2): path traversal de mídia, segredos
obrigatórios no startup, rate limit do generate-copy, IP real atrás do
proxy Flask, mensagem de login genérica e _require_admin 403."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import config as config_module
from api import database as database_module
from api.main import app
from api.routers import auth as auth_module
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

def _img(fmt: str) -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format=fmt)
    return buf.getvalue()


JPEG = _img("JPEG")
PNG = _img("PNG")


@pytest.fixture
def auth_client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app)
    app.dependency_overrides.clear()


def _fake_supabase(monkeypatch, tables: dict):
    """MagicMock encadeável; `tables[name]` é o `.data` do execute()."""
    fake = MagicMock()

    def table(name):
        q = MagicMock()
        for m in ("select", "eq", "single", "maybe_single", "order", "insert", "delete", "is_"):
            getattr(q, m).return_value = q
        q.execute.return_value = MagicMock(data=tables.get(name, []))
        return q

    fake.table.side_effect = table
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)
    return fake


# ── 1. Path traversal no upload/remoção de mídia ─────────────────────────────

@pytest.mark.parametrize("name", [
    "../../evil.jpg", "/tmp/x.jpg", "..\\x.jpg", "..\\..\\x.jpg",
    "a\x00.jpg", "foto.jpg",
])
def test_upload_generates_server_side_key_never_from_client_name(auth_client, monkeypatch, tmp_path, name):
    fake = _fake_supabase(monkeypatch, {
        "posts": {"id": 9999, "user_id": 42},
        "medias": [{"id": 1}],
    })
    root = tmp_path / "media"
    monkeypatch.setattr(posts_module, "MEDIA_ROOT", root)

    res = auth_client.post("/posts/9999/media", files={"file": (name, JPEG, "image/jpeg")})

    assert res.status_code == 201, res.text
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]  # nada vai para o disco
    key = fake.storage.from_.return_value.upload.call_args.args[0]
    assert key.startswith("posts/42/profile-a/9999/") and key.endswith(".jpg")
    # extensão vem dos magic bytes (JPEG), nunca do nome do cliente
    assert ".." not in key and "evil" not in key and "\\" not in key


@pytest.mark.parametrize(("name", "content", "ctype"), [
    ("foto.jpg", PNG, "image/jpeg"),   # nome/tipo mentem sobre o conteúdo
    ("evil.php", JPEG, "image/jpeg"),  # extensão fora da allowlist
])
def test_upload_rejects_content_that_disagrees_with_name(auth_client, monkeypatch, name, content, ctype):
    fake = _fake_supabase(monkeypatch, {"posts": {"id": 9999, "user_id": 42}, "medias": [{"id": 1}]})

    res = auth_client.post("/posts/9999/media", files={"file": (name, content, ctype)})

    assert res.status_code == 415
    fake.storage.from_.return_value.upload.assert_not_called()


def test_delete_media_refuses_path_outside_media_root(auth_client, monkeypatch, tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("nao apague")
    _fake_supabase(monkeypatch, {
        "posts": {"id": 9999, "user_id": 42},
        "medias": {"file_path": str(root / ".." / "secret.txt")},
    })
    monkeypatch.setattr(posts_module, "MEDIA_ROOT", root)

    res = auth_client.delete("/posts/9999/media/1")

    assert res.status_code == 200
    assert outside.exists()


def test_delete_media_removes_file_inside_media_root(auth_client, monkeypatch, tmp_path):
    root = tmp_path / "media"
    (root / "9999").mkdir(parents=True)
    inside = root / "9999" / "a.jpg"
    inside.write_bytes(JPEG)
    _fake_supabase(monkeypatch, {
        "posts": {"id": 9999, "user_id": 42},
        "medias": {"file_path": str(inside)},
    })
    monkeypatch.setattr(posts_module, "MEDIA_ROOT", root)

    res = auth_client.delete("/posts/9999/media/1")

    assert res.status_code == 200
    assert not inside.exists()


def test_remove_media_file_helper_confines_to_media_root(monkeypatch, tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    outside = tmp_path / "x.txt"
    outside.write_text("x")
    monkeypatch.setattr(posts_module, "MEDIA_ROOT", root)

    posts_module._remove_media_file(str(outside))
    posts_module._remove_media_file(str(root / ".." / "x.txt"))

    assert outside.exists()


# ── 2. Segredos obrigatórios no startup ──────────────────────────────────────

VALID_FERNET = "e7lc8f3AsY0VNg7Kpy1K5umJirUK6jwqkJg7_xhn0IY="


@pytest.mark.parametrize("secret", ["", "abc12", "x" * 31])
def test_validate_secrets_rejects_missing_or_short_api_secret(monkeypatch, secret):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", VALID_FERNET)
    with pytest.raises(RuntimeError, match="API_SECRET_KEY") as exc:
        config_module.validate_secrets(SimpleNamespace(api_secret_key=secret))
    if secret:
        assert secret not in str(exc.value)  # nunca ecoa o valor


@pytest.mark.parametrize("key", [None, "", "nao-e-fernet"])
def test_validate_secrets_rejects_missing_or_invalid_encryption_key(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("APP_ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("APP_ENCRYPTION_KEY", key)
    with pytest.raises(RuntimeError, match="APP_ENCRYPTION_KEY") as exc:
        config_module.validate_secrets(SimpleNamespace(api_secret_key="s" * 32))
    if key:
        assert key not in str(exc.value)


def test_validate_secrets_accepts_valid_config(monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", VALID_FERNET)
    config_module.validate_secrets(SimpleNamespace(api_secret_key="s" * 32))


# ── 4. Rate limit do generate-copy ───────────────────────────────────────────

def test_generate_copy_is_rate_limited_per_user(auth_client, monkeypatch):
    import apis.llm

    _fake_supabase(monkeypatch, {"products": {"id": 1, "name": "x"}})
    monkeypatch.setattr(apis.llm, "complete", lambda *_a, **_k: "texto")
    # chave de IA agora é por usuário (ai_credentials): aqui só importa o limite
    from api.routers import credentials as credentials_module
    monkeypatch.setattr(credentials_module, "resolve_ai_key", lambda *_a, **_k: ("gemini", "k", None))

    codes = [
        auth_client.post("/posts/generate-copy", json={"product_id": 1}).status_code
        for _ in range(auth_module._LOGIN_RATE_LIMIT_ATTEMPTS + 1)
    ]

    assert codes[:-1] == [200] * auth_module._LOGIN_RATE_LIMIT_ATTEMPTS
    assert codes[-1] == 429

    app.dependency_overrides[get_current_user_id] = lambda: 43
    assert auth_client.post("/posts/generate-copy", json={"product_id": 1}).status_code == 200


# ── 5. IP real atrás do proxy Flask ──────────────────────────────────────────

def _req(host, xff=None):
    headers = {"x-forwarded-for": xff} if xff else {}
    return SimpleNamespace(client=SimpleNamespace(host=host), headers=headers)


def test_client_ip_uses_forwarded_for_only_from_loopback_proxy():
    assert auth_module.client_ip(_req("127.0.0.1", "203.0.113.9")) == "203.0.113.9"
    assert auth_module.client_ip(_req("::1", "1.1.1.1, 203.0.113.9")) == "203.0.113.9"
    assert auth_module.client_ip(_req("127.0.0.1")) == "127.0.0.1"
    # cliente direto (não é o proxy local) não consegue forjar o IP
    assert auth_module.client_ip(_req("198.51.100.7", "203.0.113.9")) == "198.51.100.7"
    assert auth_module.client_ip(SimpleNamespace(client=None, headers={})) == "unknown"


def test_login_lockout_of_one_ip_does_not_block_other_ips(monkeypatch):
    """Atrás do proxy todo mundo chega como 127.0.0.1: sem X-Forwarded-For,
    5 senhas erradas de um atacante travavam o login do admin pra todos."""
    fake = _fake_supabase(monkeypatch, {"users": []})
    monkeypatch.setattr(auth_module, "get_supabase", lambda: fake)
    # TestClient conecta como "testclient": trata como o proxy local
    monkeypatch.setattr(auth_module, "_TRUSTED_PROXY_HOSTS", {"testclient"})
    c = TestClient(app)
    form = {"username": "rafastudio", "password": "errada"}

    for _ in range(auth_module._LOGIN_RATE_LIMIT_ATTEMPTS):
        c.post("/auth/login", data=form, headers={"X-Forwarded-For": "203.0.113.66"})
    assert c.post("/auth/login", data=form, headers={"X-Forwarded-For": "203.0.113.66"}).status_code == 429

    res = c.post("/auth/login", data=form, headers={"X-Forwarded-For": "198.51.100.1"})
    assert res.status_code == 401


# ── 6. Mensagem de login não revela se o usuário existe ──────────────────────

def test_login_same_message_for_unknown_user_and_wrong_password(monkeypatch):
    from passlib.context import CryptContext

    c = TestClient(app)
    fake = _fake_supabase(monkeypatch, {"users": []})
    monkeypatch.setattr(auth_module, "get_supabase", lambda: fake)
    unknown = c.post("/auth/login", data={"username": "ninguem", "password": "x"})

    hashed = CryptContext(schemes=["bcrypt"]).hash("certa-123")
    fake = _fake_supabase(monkeypatch, {"users": [{"id": 1, "username": "rafa", "password": hashed}]})
    monkeypatch.setattr(auth_module, "get_supabase", lambda: fake)
    wrong = c.post("/auth/login", data={"username": "rafa", "password": "errada"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"] == "Usuário ou senha inválidos"


# ── 9. _require_admin sem linha do usuário → 403 (não 500) ───────────────────

def test_require_admin_returns_403_when_user_row_missing(auth_client, monkeypatch):
    fake = MagicMock()
    q = fake.table.return_value
    for m in ("select", "eq", "order", "limit"):
        getattr(q, m).return_value = q
    q.single.return_value.execute.side_effect = Exception("PGRST116 0 rows")
    q.maybe_single.return_value.execute.return_value = None
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake)

    assert auth_client.get("/users").status_code == 403
