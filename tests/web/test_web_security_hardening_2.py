"""Auditoria de segurança (lote 2), lado Flask: CORS restrito, IP real
repassado ao FastAPI, segredo interno com compare_digest e /startup sem
senha no log nem bootstrap aberto."""

from unittest.mock import MagicMock, patch

from shopee_bot.web.helpers import cors_origins
from shopee_bot.web.routes import startup as startup_module


# ── 3. CORS ──────────────────────────────────────────────────────────────────

def test_cors_origins_reads_json_csv_and_frontend_url(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://a.example", "https://b.example/"]')
    monkeypatch.setenv("FRONTEND_URL", "https://app.example")
    assert cors_origins() == ["https://a.example", "https://app.example", "https://b.example"]

    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://c.example")
    monkeypatch.delenv("FRONTEND_URL")
    assert cors_origins() == ["https://a.example", "https://c.example"]


def test_cors_origins_empty_when_nothing_configured(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    assert cors_origins() == []


def test_cors_does_not_allow_arbitrary_origin(client):
    res = client.get("/health", headers={"Origin": "https://evil.example"})
    assert res.headers.get("Access-Control-Allow-Origin") not in ("*", "https://evil.example")


# ── 5. Proxy repassa o IP real (não o X-Forwarded-For forjado) ───────────────

def test_proxy_replaces_forwarded_for_with_resolved_client_ip(client):
    with patch("shopee_bot.web.routes.api_proxy.requests.request") as mock_req:
        mock_req.return_value = MagicMock(status_code=200, content=b"{}", raw=MagicMock(headers={}))
        client.post(
            "/api/auth/login",
            # browser forjou "6.6.6.6"; o LB do Render anexou o IP real
            headers={"X-Forwarded-For": "6.6.6.6, 198.51.100.9"},
            environ_base={"REMOTE_ADDR": "203.0.113.5"},
        )

    sent = {k.lower(): v for k, v in mock_req.call_args.kwargs["headers"].items()}
    # ProxyFix(x_for=1) usa o último hop (o do LB) como IP real
    assert sent["x-forwarded-for"] == "198.51.100.9"


# ── 7. Segredo interno ───────────────────────────────────────────────────────

def test_internal_secret_rejects_wrong_and_non_ascii(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_SECRET", "segredo-certo")
    for given in ("segredo-errado", "segredo-certé"):
        res = client.post("/internal/scheduler/jobs", json={}, headers={"X-Internal-Secret": given})
        assert res.status_code == 403


# ── 8. /startup ──────────────────────────────────────────────────────────────

def test_startup_disabled_without_env_password(client, monkeypatch):
    monkeypatch.delenv("STARTUP_ADMIN_PASSWORD", raising=False)
    with patch.object(startup_module.users, "count") as count:
        res = client.get("/startup")
    assert res.status_code == 404
    count.assert_not_called()


def test_startup_uses_env_password_and_never_logs_it(client, monkeypatch):
    fake_pw = "test-only"  # valor de teste, não é segredo real
    monkeypatch.setenv("STARTUP_ADMIN_PASSWORD", fake_pw)
    conn = MagicMock()
    with patch.object(startup_module.users, "count", return_value=0), \
            patch.object(startup_module.users, "insert", return_value="uid") as insert, \
            patch.object(startup_module, "get_conn", return_value=conn), \
            patch.object(startup_module, "put_conn"), \
            patch.object(startup_module, "logger") as log, \
            patch.multiple(
                startup_module,
                shopee_credentials=MagicMock(), threads_credentials=MagicMock(),
                x_credentials=MagicMock(), facebook_credentials=MagicMock(),
                instagram_credentials=MagicMock(), tiktok_credentials=MagicMock(),
                kwai_credentials=MagicMock(),
            ):
        res = client.get("/startup")

    assert res.status_code == 302
    assert insert.call_args.args[0]["password"] == fake_pw
    logged = " ".join(str(c) for c in log.mock_calls)
    assert fake_pw not in logged


def test_geolocation_permission_policy_limits_access_to_same_origin(client):
    """O popup de GPS precisa funcionar em HTTPS, sem habilitar embeds/terceiros."""
    res = client.get("/health")
    policy = res.headers.get("Permissions-Policy", "")
    assert "geolocation=(self)" in policy
    assert "camera=()" in policy
    assert "microphone=()" in policy
