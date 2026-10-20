import os
import sys
import tempfile
import types
from pathlib import Path

os.environ.setdefault("FLASK_MAX_CONTENT_LENGTH", "52428800")
os.environ.setdefault("FLASK_SESSION_SECRET", "test_only_secret")
os.environ.setdefault("FLASK_UPLOAD_FOLDER", tempfile.gettempdir())
os.environ.setdefault("FLASK_DEBUG", "False")

project_root = Path(__file__).resolve().parents[2]
if "shopee_bot" not in sys.modules:
    package = types.ModuleType("shopee_bot")
    package.__path__ = [str(project_root)]
    sys.modules["shopee_bot"] = package

from shopee_bot.web import DEBUG, app


def test_false_debug_value_does_not_enable_debug_mode():
    assert DEBUG is False


def test_csp_does_not_allow_dynamic_code_execution():
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert "'unsafe-eval'" not in response.headers["Content-Security-Policy"]


def test_spa_csp_blocks_inline_scripts():
    with app.test_client() as client:
        response = client.get("/")
    policy = response.headers["Content-Security-Policy"]
    assert "script-src 'self';" in policy
    assert "'unsafe-inline'" not in policy.split("script-src ", 1)[1].split(";", 1)[0]


def test_spa_startup_has_no_inline_script_or_handler():
    html = (project_root / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "onclick=" not in html
    assert 'src="/splash.js"' in html
