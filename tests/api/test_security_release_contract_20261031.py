"""Regression contracts for the 2026-10-31 security evidence review.

Read-only / in-process verification. No network, database writes, credential
inspection, external publication or brute-force traffic is performed.
These checks support a technical review, NOT an independent penetration test.
"""

from types import SimpleNamespace

import pytest

from api.config import Settings, validate_secrets
from api.main import app
from apis.shopee_video import (
    ShopeeVideoAuthorization,
    ShopeeVideoClient,
    ShopeeVideoError,
)


def test_api_disables_interactive_documentation():
    """Public Swagger, ReDoc and OpenAPI discovery are not registered."""
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert not {"/docs", "/redoc", "/openapi.json"} & paths


def test_cors_rejects_wildcard_and_null_origins():
    """Credentialed CORS should use explicit origins only."""
    values = Settings._explicit_cors_origins(
        ["*", "null", "https://example.test/", "https://example.test"]
    )
    assert values == ["https://example.test"]


def test_short_session_secret_fails_closed():
    """Missing/short JWT secret is rejected without logging its value."""
    secret = "short-test-secret"
    with pytest.raises(RuntimeError) as err:
        validate_secrets(SimpleNamespace(api_secret_key=secret))
    assert "API_SECRET_KEY" in str(err.value)
    assert secret not in str(err.value)


def test_shopee_video_requires_explicit_authorization_and_feature_gate():
    """No API calls are possible simply by providing mock credentials."""
    auth = ShopeeVideoAuthorization(
        partner_id=123,
        partner_key="fixture-key",
        user_id=456,
        access_token="fixture-token",
        permission_granted=False,
    )
    with pytest.raises(ShopeeVideoError, match="autorização"):
        ShopeeVideoClient(auth, enabled=True)
    with pytest.raises(ShopeeVideoError, match="autorização"):
        ShopeeVideoClient(auth, enabled=False)


def test_shopee_video_routes_are_limited_to_oauth_status_and_preview():
    """Shopee Vídeo expõe só OAuth, status e prévia; nada de upload ou postagem.

    A rota /shopee-video existe desde o OAuth de afiliado (migration 091). Este
    contrato antigo exigia que nenhuma rota existisse; agora exige que a lista
    seja exatamente a esperada, para que publicar não seja ligado em silêncio.
    Ao liberar a publicação, atualize esta lista junto com o publicador.
    """
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    shopee_video_paths = {p for p in paths if "shopee-video" in p}
    assert shopee_video_paths == {
        "/admin/shopee-video",
        "/shopee-video/status",
        "/shopee-video/authorize",
        "/shopee-video/callback",
        "/shopee-video/refresh",
        "/shopee-video/authorization",
        "/shopee-video/preview",
    }
