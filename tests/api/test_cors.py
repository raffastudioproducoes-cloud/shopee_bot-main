"""F-05: CORS com credenciais so para origens explicitas (nunca '*')."""

from fastapi.testclient import TestClient

from api.config import Settings
from api.main import app


def _preflight(origin, headers="content-type", method="POST"):
    return TestClient(app).options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_allowed_origin_gets_credentials():
    res = _preflight("http://localhost:5173")

    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert res.headers["access-control-allow-credentials"] == "true"


def test_unknown_origin_gets_no_cors_headers():
    res = _preflight("https://evil.example")

    assert "access-control-allow-origin" not in res.headers


def test_preflight_does_not_reflect_arbitrary_headers_or_methods():
    assert _preflight("http://localhost:5173", headers="x-evil-header").status_code == 400
    assert _preflight("http://localhost:5173", method="TRACE").status_code == 400


def test_wildcard_and_null_origins_are_dropped_from_settings():
    cfg = Settings(cors_origins=["*", "null", "https://app.example.com/", "https://stg.example.com"])

    assert cfg.cors_origins == ["https://app.example.com", "https://stg.example.com"]


def test_settings_default_is_localhost_only():
    assert all(o.startswith("http://localhost") for o in Settings().cors_origins)
