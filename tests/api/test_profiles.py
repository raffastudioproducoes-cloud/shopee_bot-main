"""Testes do router de perfis (FastAPI) -- cotas por plano via RPC, perfil principal
protegido contra exclusao, e ativacao de perfil (troca de cookie).

Duas diferencas em relacao ao brief original (task-5-brief.md), ambas
autorizadas la mesmo pra manter o comportamento testado:

1. Fixtures `client`/`auth_client` seguem o padrao real de
   tests/api/test_users.py (app.dependency_overrides sobre
   `get_current_user_id`) -- `client`/`auth_headers` com cookies reais nao
   existem em tests/api/conftest.py.
2. Mock do Supabase via `monkeypatch.setattr(database_module, "get_supabase",
   ...)` -- igual test_users.py/test_auth.py -- em vez de
   `patch("api.routers.profiles.supabase")` direto: `supabase` e um proxy
   (`api/database.py::_SupabaseProxy`) cujo `__getattr__` chama
   `get_supabase()` de verdade; no Python usado aqui (3.14),
   `unittest.mock.patch` sonda `hasattr(obj, "__func__")` no objeto
   ORIGINAL antes de substitui-lo, o que disparou esse `__getattr__` e
   levantou `RuntimeError: SUPABASE_URL and SUPABASE_KEY must be
   configured` (sem SUPABASE_URL/KEY configurados no ambiente de teste).
   Patchar a funcao de origem evita o proxy ser tocado.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import database as database_module
from api.main import app
from api.routers.auth import _create_token, get_current_user_id

USER_ID = "u-1"


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Cliente autenticado (user_id=USER_ID) -- mesmo padrao de test_users.py."""
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    return TestClient(app)


def _mock_supabase(monkeypatch, execute_return):
    """Mocka `supabase.table(...)` encadeado (select/eq/maybe_single/update/
    delete/insert todos retornam o proprio mock, permitindo qualquer numero
    de `.eq(...)` em sequencia) devolvendo `execute_return` em toda chamada
    de `.execute()`."""
    fake_client = MagicMock()
    query = fake_client.table.return_value
    for method in ("select", "eq", "is_", "maybe_single", "update", "delete", "insert"):
        getattr(query, method).return_value = query
    query.execute.return_value = MagicMock(data=execute_return)
    fake_client.rpc.return_value = query
    query._fake_client = fake_client
    monkeypatch.setattr(database_module, "get_supabase", lambda: fake_client)
    from contextlib import nullcontext
    from api.routers import profiles as profiles_module
    monkeypatch.setattr(profiles_module, "storage_upload_reservation", lambda size: nullcontext())
    return query


def test_create_profile_maps_plan_cap_rejection_to_403(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = Exception("profile_limit_exceeded")
    response = auth_client.post(
        "/profiles", json={"nome": "Loja adicional", "email": "loja4@example.com"}
    )
    assert response.status_code == 403
    assert "limite" in response.json()["detail"].lower()


def test_delete_principal_profile_is_blocked(auth_client, monkeypatch):
    _mock_supabase(
        monkeypatch, {"id": "p-1", "user_id": USER_ID, "kind": "principal"}
    )
    response = auth_client.delete("/profiles/p-1")
    assert response.status_code == 400


def test_delete_secondary_profile_is_fail_closed_until_archive_rollout(auth_client, monkeypatch):
    query = _mock_supabase(
        monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"}
    )
    monkeypatch.delenv("PROFILE_ARCHIVAL_ENABLED", raising=False)
    response = auth_client.delete("/profiles/p-2")
    assert response.status_code == 503
    assert "Nenhum perfil" in response.json()["detail"]
    query.delete.assert_not_called()
    query._fake_client.rpc.assert_not_called()


def test_delete_secondary_profile_archives_via_transactional_rpc(auth_client, monkeypatch):
    query = _mock_supabase(
        monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"}
    )
    monkeypatch.setenv("PROFILE_ARCHIVAL_ENABLED", "true")
    response = auth_client.delete("/profiles/p-2")
    assert response.status_code == 200
    assert response.json() == {"status": "archived"}
    query._fake_client.rpc.assert_called_once_with("archive_profile_with_history", {
        "p_user_id": USER_ID, "p_profile_id": "p-2",
    })
    query.delete.assert_not_called()


def test_archive_rpc_failure_preserves_profile_and_returns_503(auth_client, monkeypatch):
    query = _mock_supabase(
        monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"}
    )
    monkeypatch.setenv("PROFILE_ARCHIVAL_ENABLED", "true")
    query.execute.side_effect = [MagicMock(data={"id": "p-2", "kind": "secundario"}),
                                 Exception("transient failure")]
    response = auth_client.delete("/profiles/p-2")
    assert response.status_code == 503
    query.delete.assert_not_called()


def test_create_profile_requires_auth(client):
    response = client.post("/profiles", json={"nome": "Loja", "email": "a@b.com"})
    assert response.status_code == 401


def test_delete_profile_not_found_returns_404(auth_client, monkeypatch):
    _mock_supabase(monkeypatch, None)
    response = auth_client.delete("/profiles/does-not-exist")
    assert response.status_code == 404


def test_missing_profile_sdk_returns_none_not_500(monkeypatch):
    from api.routers.profiles import _get_own_profile_or_404

    query = _mock_supabase(monkeypatch, None)
    query.execute.return_value = None
    with pytest.raises(HTTPException) as error:
        _get_own_profile_or_404("foreign", USER_ID)
    assert error.value.status_code == 404


def test_update_profile_of_another_user_returns_404(auth_client, monkeypatch):
    """IDOR: usuario A autenticado tenta PUT num profile_id que pertence ao
    usuario B -- a query `.eq('id', ...).eq('user_id', ...)` em
    `_get_own_profile_or_404` nao encontra nada (perfil e de outra conta) e
    deve devolver 404, mesmo comportamento ja testado em delete/activate."""
    _mock_supabase(monkeypatch, None)
    response = auth_client.put(
        "/profiles/p-of-another-user",
        json={"nome": "Hack", "email": "hack@example.com"},
    )
    assert response.status_code == 404


def test_activate_profile_copies_login_cookie_flags(auth_client, monkeypatch):
    """Verifica que /profiles/{id}/activate seta o cookie `access_token`
    com os MESMOS flags do login (httponly, secure, samesite=lax,
    max_age=86400) -- checagem pontual pedida no brief da Task 5."""
    token = _create_token({"sub": "testuser", "id": USER_ID})
    auth_client.cookies.set("access_token", token)

    _mock_supabase(
        monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"}
    )
    from api.routers import profiles as profiles_module
    monkeypatch.setattr(
        profiles_module, "_get_user_from_supabase",
        lambda username: {"id": USER_ID, "password": "h"},
    )
    response = auth_client.post("/profiles/p-2/activate")

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "max-age=86400" in set_cookie.lower()


def test_avatar_upload_rejects_non_image_content(auth_client, monkeypatch):
    """Difere do brief (task-7-brief.md Step 1): não existe fixture
    `client`/`auth_headers` com cookies reais neste arquivo (ver nota no
    topo do módulo) -- usa `auth_client`/`_mock_supabase`, mesmo padrão
    das demais rotas de profiles."""
    _mock_supabase(monkeypatch, {"id": "p-1", "user_id": USER_ID})
    fake_file = ("avatar.png", b"isso nao e uma imagem de verdade", "image/png")
    response = auth_client.post(
        "/profiles/p-1/avatar",
        files={"file": fake_file},
    )
    assert response.status_code == 400


def _img(fmt, **kw):
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format=fmt, **kw)
    return buf.getvalue()


def test_avatar_upload_succeeds_and_updates_avatar_url(auth_client, monkeypatch):
    """PNG real -- deve subir pro bucket `avatars`, atualizar
    `profiles.avatar_url` e devolver a URL pública."""
    _mock_supabase(monkeypatch, {"id": "p-1", "user_id": USER_ID})
    fake_client = database_module.get_supabase()
    fake_client.storage.from_.return_value.get_public_url.return_value = (
        "https://supabase.example/storage/v1/object/public/avatars/p-1/avatar.png"
    )

    response = auth_client.post(
        "/profiles/p-1/avatar",
        files={"file": ("avatar.png", _img("PNG"), "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "avatar_url": "https://supabase.example/storage/v1/object/public/avatars/p-1/avatar.png"
    }
    fake_client.storage.from_.assert_called_with("avatars")
    fake_client.storage.from_.return_value.upload.assert_called_once()


def test_avatar_is_reencoded_without_metadata(auth_client, monkeypatch):
    from io import BytesIO

    from PIL import Image

    _mock_supabase(monkeypatch, {"id": "p-1", "user_id": USER_ID})
    fake_client = database_module.get_supabase()
    raw = _img("JPEG", comment=b"<script>x</script>", icc_profile=b"<script>icc</script>")

    response = auth_client.post("/profiles/p-1/avatar", files={"file": ("a.jpg", raw, "image/jpeg")})

    assert response.status_code == 200
    path, uploaded, options = fake_client.storage.from_.return_value.upload.call_args.args
    assert path == "p-1/avatar.jpg" and options["content-type"] == "image/jpeg"
    assert b"<script>" not in uploaded
    info = Image.open(BytesIO(uploaded)).info
    assert not [k for k in ("comment", "icc_profile", "exif", "xmp") if k in info]


@pytest.mark.parametrize("content", [
    _img("GIF"),                              # GIF não é formato de avatar
    b"\xff\xd8\xff" + bytes(40),  # JPEG truncado/corrompido
])
def test_avatar_upload_rejects_disallowed_or_corrupt_images(auth_client, monkeypatch, content):
    _mock_supabase(monkeypatch, {"id": "p-1", "user_id": USER_ID})
    fake_client = database_module.get_supabase()

    response = auth_client.post("/profiles/p-1/avatar", files={"file": ("avatar.png", content, "image/png")})

    assert response.status_code == 400
    fake_client.storage.from_.return_value.upload.assert_not_called()


def test_avatar_upload_rejects_file_over_max_size(auth_client, monkeypatch):
    """MEDIUM do security-reviewer (fix round 1): arquivo maior que
    MAX_AVATAR_BYTES (5MB) deve ser rejeitado com 413, sem chegar a subir
    pro storage -- mesmo padrão de posts.py::MAX_MEDIA_BYTES."""
    from api.routers import profiles as profiles_router

    _mock_supabase(monkeypatch, {"id": "p-1", "user_id": USER_ID})
    fake_client = database_module.get_supabase()

    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * profiles_router.MAX_AVATAR_BYTES
    response = auth_client.post(
        "/profiles/p-1/avatar",
        files={"file": ("avatar.png", oversized, "image/png")},
    )

    assert response.status_code == 413
    fake_client.storage.from_.return_value.upload.assert_not_called()


def test_list_profiles_recovers_one_http2_read_error(auth_client, monkeypatch):
    """Uma desconexão transiente não pode derrubar a lista de perfis."""
    import httpx

    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = [
        httpx.ReadError("connection temporarily unavailable"),
        MagicMock(data=[{"id": "p-main", "user_id": USER_ID}]),
    ]

    response = auth_client.get("/profiles")

    assert response.status_code == 200
    assert response.json() == [{"id": "p-main", "user_id": USER_ID}]
    query.eq.assert_called_with("user_id", USER_ID)
    assert query.execute.call_count == 2


def test_list_profiles_two_transport_failures_return_503_not_500(auth_client, monkeypatch):
    """Falha persistente nega a leitura com 503 sanitizado; não inventa lista."""
    import httpx

    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = [
        httpx.ReadError("connection temporarily unavailable"),
        httpx.RemoteProtocolError("GOAWAY"),
    ]

    response = auth_client.get("/profiles")

    assert response.status_code == 503
    assert "Resource temporarily unavailable" not in response.text
    assert query.execute.call_count == 2


def test_profile_resolution_retries_owned_read_only_after_http2_disconnect(monkeypatch, real_profile_resolution):
    """A queda HTTP/2 não invalida a sessão nem remove seu perfil."""
    import httpx
    from api.routers.profiles import _resolve_profile_id

    query = _mock_supabase(monkeypatch, {"id": "p-2"})
    query.execute.side_effect = [
        httpx.RemoteProtocolError("GOAWAY"),
        MagicMock(data={"id": "p-2"}),
    ]

    assert _resolve_profile_id("p-2", USER_ID) == "p-2"
    assert query.execute.call_count == 2


def test_profile_resolution_retries_principal_fallback_after_http2_disconnect(monkeypatch, real_profile_resolution):
    """Somente leitura do fallback é repetida; continua escopada ao titular."""
    import httpx
    from api.routers.profiles import _resolve_profile_id

    query = _mock_supabase(monkeypatch, None)
    query.execute.side_effect = [
        MagicMock(data=None),
        httpx.RemoteProtocolError("GOAWAY"),
        MagicMock(data={"id": "p-main"}),
    ]

    assert _resolve_profile_id("p-invalido", USER_ID) == "p-main"
    assert query.execute.call_count == 3


def test_profile_resolution_fails_closed_after_two_http2_disconnects(monkeypatch, real_profile_resolution):
    """Duas falhas transitórias retornam 503, nunca perfil sem dono/401."""
    import httpx
    from api.routers.profiles import _resolve_profile_id

    query = _mock_supabase(monkeypatch, None)
    query.execute.side_effect = [
        httpx.RemoteProtocolError("GOAWAY"),
        httpx.RemoteProtocolError("GOAWAY"),
    ]

    with pytest.raises(HTTPException) as error:
        _resolve_profile_id("p-2", USER_ID)
    assert error.value.status_code == 503
    assert query.execute.call_count == 2


class TestCurrentProfileIdValidation:
    """O `profile_id` do token só vale se pertencer ao usuário; senão cai
    no perfil principal."""

    @staticmethod
    def _fake(owned, principal):
        results = iter([MagicMock(data=owned), MagicMock(data=principal)])
        fake_client = MagicMock()
        query = fake_client.table.return_value
        for method in ("select", "eq", "maybe_single"):
            getattr(query, method).return_value = query
        query.execute.side_effect = lambda: next(results)
        return fake_client

    def test_returns_token_profile_when_owned(self, monkeypatch, real_profile_resolution):
        from api.routers.profiles import _resolve_profile_id

        monkeypatch.setattr(
            database_module, "get_supabase", (lambda c=self._fake({"id": "p-2"}, None): c)
        )
        assert _resolve_profile_id("p-2", USER_ID) == "p-2"

    def test_falls_back_to_principal_when_not_owned(self, monkeypatch, real_profile_resolution):
        from api.routers.profiles import _resolve_profile_id

        monkeypatch.setattr(
            database_module, "get_supabase", (lambda c=self._fake(None, {"id": "p-main"}): c)
        )
        assert _resolve_profile_id("p-alheio", USER_ID) == "p-main"

    def test_returns_none_when_no_principal(self, monkeypatch, real_profile_resolution):
        from api.routers.profiles import _resolve_profile_id

        monkeypatch.setattr(
            database_module, "get_supabase", (lambda c=self._fake(None, None): c)
        )
        assert _resolve_profile_id("p-alheio", USER_ID) is None


def _create_payload():
    return {"nome": "Novo", "email": "novo@example.com"}


def test_create_profile_maps_db_trigger_limit_error_to_403(auth_client, monkeypatch):
    """Limite negado atomicamente pelo banco: API retorna 403 amigável."""
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = Exception("profile_limit_exceeded")
    response = auth_client.post("/profiles", json=_create_payload())
    assert response.status_code == 403
    assert "Limite" in response.json()["detail"]


def test_create_profile_unexpected_db_error_returns_generic_500(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = Exception("conn string secreta")
    response = auth_client.post("/profiles", json=_create_payload())
    assert response.status_code == 500
    assert "secreta" not in response.text


def test_create_profile_is_rate_limited(auth_client, monkeypatch):
    _mock_supabase(monkeypatch, [{"id": "p"}, {"id": "q"}, {"id": "r"}])
    codes = [auth_client.post("/profiles", json=_create_payload()).status_code for _ in range(6)]
    assert codes[-1] == 429


def test_activate_recomputes_pwv_from_current_hash_for_legacy_token(auth_client, monkeypatch):
    """Token legado (sem pwv) deve ganhar pwv do hash atual ao trocar de perfil."""
    from api.routers import profiles as profiles_module
    from api.routers.auth import _decode_token, _password_version

    auth_client.cookies.set("access_token", _create_token({"sub": "testuser", "id": USER_ID}))
    _mock_supabase(monkeypatch, {"id": "p-2", "user_id": USER_ID, "kind": "secundario"})
    monkeypatch.setattr(
        profiles_module, "_get_user_from_supabase",
        lambda username: {"id": USER_ID, "password": "hash-atual"},
    )
    response = auth_client.post("/profiles/p-2/activate")
    assert response.status_code == 200
    new_token = response.headers["set-cookie"].split("access_token=")[1].split(";")[0]
    assert _decode_token(new_token)["pwv"] == _password_version("hash-atual")


def test_create_profile_uses_atomic_rpc_and_never_trusts_tier_from_browser(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [{"id": "new-profile"}])
    response = auth_client.post("/profiles", json={
        "nome": "Loja quatro", "email": "loja4@example.com",
        "plan_tier": "premium", "access": "ADMIN",
    })
    assert response.status_code == 201
    call = query._fake_client.rpc.call_args
    assert call.args[0] == "insert_profile_with_plan_quota"
    assert call.args[1]["p_user_id"] == USER_ID
    assert "plan_tier" not in call.args[1]
    assert "access" not in call.args[1]


def test_create_profile_needs_only_name_and_does_not_duplicate_account_contacts(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [{"id": "new-profile"}])
    response = auth_client.post("/profiles", json={"nome": "Ofertas do Rafa"})
    assert response.status_code == 201
    args = query._fake_client.rpc.call_args.args[1]
    assert args["p_nome"] == "Ofertas do Rafa"
    assert args["p_email"] is None
    assert args["p_telefone"] is None
    assert args["p_endereco"] is None


def test_update_only_profile_name_preserves_legacy_contact_fields(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [{"id": "p-2", "user_id": USER_ID}])
    response = auth_client.put("/profiles/p-2", json={"nome": "Nome renovado"})
    assert response.status_code == 200
    query.update.assert_called_once_with({"nome": "Nome renovado"})


def test_list_profiles_returns_only_card_fields(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    response = auth_client.get("/profiles")
    assert response.status_code == 200
    query.select.assert_called_once_with("id,user_id,kind,plan_tier,nome,avatar_url")


def test_create_profile_rejects_policy_unavailable(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = Exception("plan_policy_unavailable")
    response = auth_client.post("/profiles", json=_create_payload())
    assert response.status_code == 503
    assert "Política" in response.json()["detail"]


def test_profile_tiers_are_enforced_by_database_migration_not_ui():
    from pathlib import Path
    sql = (Path(__file__).resolve().parents[2] /
           "database/migrations/072_plan_limits_and_atomic_catalog_quotas.sql").read_text()
    assert "('free',100,20,1,1,0,0,0,1,false)" in sql
    assert "('pro',500,20,3,5,2,15,3,3,false)" in sql
    assert "('premium',2000,100,5,5,5,30,15,5,true)" in sql
    assert "p_user_id uuid,p_nome text,p_email text" in sql
    assert "v_access <> 'ADMIN'" in sql
    assert "profile_limit_exceeded" in sql


def test_get_profile_quota_reads_server_policy_for_premium(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = [
        MagicMock(data={"access": "USER", "plan_tier": "premium"}),
        MagicMock(data={"max_profiles_per_account": 5}),
        MagicMock(data=[{"id": "principal"}, {"id": "segundo"}, {"id": "terceiro"}]),
    ]
    response = auth_client.get("/profiles/quota")
    assert response.status_code == 200
    assert response.json() == {"tier": "premium", "used": 3, "limit": 5, "unlimited": False}


def test_get_profile_quota_admin_ignores_commercial_max(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = [
        MagicMock(data={"access": "ADMIN", "plan_tier": "free"}),
        MagicMock(data=[{"id": "principal"}]),
    ]
    response = auth_client.get("/profiles/quota")
    assert response.status_code == 200
    assert response.json() == {"tier": "premium", "used": 1, "limit": None, "unlimited": True}


def test_get_profile_quota_fails_closed_without_policy(auth_client, monkeypatch):
    query = _mock_supabase(monkeypatch, [])
    query.execute.side_effect = [
        MagicMock(data={"access": "USER", "plan_tier": "pro"}),
        MagicMock(data=None),
    ]
    assert auth_client.get("/profiles/quota").status_code == 503


@pytest.mark.parametrize(
    ("endpoint", "row", "expected"),
    [
        (
            "/profiles/location-sharing",
            {"choice": "declined", "latitude": None, "longitude": None, "collected_at": None},
            {"choice": "declined", "latitude": None, "longitude": None, "collected_at": None},
        ),
        ("/profiles/gps-preference", {"gps_consented_at": "2026-11-03T00:00:00Z"}, {"enabled": True}),
        ("/profiles/region-preference", {"region": "BR-RJ"}, {"region": "BR-RJ", "consented": True}),
        (
            "/profiles/acquisition-source",
            {"source": "direct"},
            {"source": "direct", "declared": True},
        ),
    ],
)
def test_profile_preference_get_recovers_http2_transport_error(
    auth_client, monkeypatch, endpoint, row, expected
):
    """Somente SELECTs são repetidos uma vez, preservando a identidade da conta."""
    import httpx

    query = _mock_supabase(monkeypatch, [])
    query.limit.return_value = query
    query.execute.side_effect = [
        httpx.ReadError("transient HTTP/2 reset"),
        MagicMock(data=[row]),
    ]

    response = auth_client.get(endpoint)

    assert response.status_code == 200
    assert response.json() == expected
    assert query.execute.call_count == 2
    if endpoint.endswith("gps-preference"):
        query.eq.assert_called_with("id", USER_ID)
    else:
        query.eq.assert_called_with("user_id", USER_ID)


@pytest.mark.parametrize(
    "endpoint",
    [
        "/profiles/location-sharing",
        "/profiles/gps-preference",
        "/profiles/region-preference",
        "/profiles/acquisition-source",
    ],
)
def test_profile_preference_get_transport_failure_is_controlled_503(
    auth_client, monkeypatch, endpoint
):
    """Dois erros no transporte retornam 503 sem vazamento nem falsear consentimento."""
    import httpx

    query = _mock_supabase(monkeypatch, [])
    query.limit.return_value = query
    query.execute.side_effect = [
        httpx.ReadError("private endpoint unavailable"),
        httpx.RemoteProtocolError("HTTP/2 GOAWAY"),
    ]

    response = auth_client.get(endpoint)

    assert response.status_code == 503
    assert "private endpoint unavailable" not in response.text
    assert query.execute.call_count == 2
