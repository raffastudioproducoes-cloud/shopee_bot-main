import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch


project_root = Path(__file__).resolve().parents[2]
os.environ.setdefault("FLASK_MAX_CONTENT_LENGTH", "52428800")
os.environ.setdefault("FLASK_SESSION_SECRET", "test_only_secret")
os.environ.setdefault("FLASK_UPLOAD_FOLDER", tempfile.gettempdir())
if "shopee_bot" not in sys.modules:
    package = types.ModuleType("shopee_bot")
    package.__path__ = [str(project_root)]
    sys.modules["shopee_bot"] = package

from shopee_bot.web import app


def _upstream():
    response = types.SimpleNamespace(status_code=200, content=b"{}")
    response.raw = types.SimpleNamespace(headers={"Content-Type": "application/json"})
    return response


def test_cookie_mutation_rejects_foreign_or_missing_origin():
    with app.test_client() as browser:
        browser.set_cookie("access_token", "synthetic")
        for headers in (
            {"Origin": "https://evil.example"},
            {"Origin": "http://localhost.evil.example"},
            {"Origin": "https://localhost"},
            {},
        ):
            with patch("shopee_bot.web.routes.api_proxy.requests.request") as upstream:
                result = browser.post("/api/profiles", json={}, headers=headers)
            assert result.status_code == 403
            upstream.assert_not_called()


def test_cookie_mutation_accepts_matching_origin_or_referer():
    with app.test_client() as browser:
        browser.set_cookie("access_token", "synthetic")
        for headers in (
            {"Origin": "http://localhost"},
            {"Referer": "http://localhost/profiles"},
        ):
            with patch("shopee_bot.web.routes.api_proxy.requests.request", return_value=_upstream()) as upstream:
                result = browser.post("/api/profiles", json={}, headers=headers)
            assert result.status_code == 200
            upstream.assert_called_once()


def test_signed_callback_without_session_cookie_is_not_blocked():
    with app.test_client() as browser:
        with patch("shopee_bot.web.routes.api_proxy.requests.request", return_value=_upstream()) as upstream:
            result = browser.post(
                "/api/meta/data-deletion",
                data="signed_request=synthetic",
                headers={"Origin": "https://meta.example"},
            )
        assert result.status_code == 200
        upstream.assert_called_once()
