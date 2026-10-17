import sys
import types
from pathlib import Path


project_root = Path(__file__).resolve().parents[2]
if "shopee_bot" not in sys.modules:
    package = types.ModuleType("shopee_bot")
    package.__path__ = [str(project_root)]
    sys.modules["shopee_bot"] = package

from shopee_bot.web import app


def test_csp_does_not_allow_dynamic_code_execution():
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert "'unsafe-eval'" not in response.headers["Content-Security-Policy"]
