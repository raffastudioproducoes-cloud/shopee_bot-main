from fastapi.testclient import TestClient

from api.main import app


def test_interactive_api_docs_are_not_public():
    client = TestClient(app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
