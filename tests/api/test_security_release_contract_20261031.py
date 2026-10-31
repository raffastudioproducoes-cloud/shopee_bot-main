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
    paths = {route.path for route in app.routes}
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


def test_shopee_video_not_registered_as_live_api_endpoint():
    """Preparatory client must not silently enable public publishing routes."""
    paths = {route.path for route in app.routes}
    assert not any(path.startswith("/shopee-video") for path in paths)
