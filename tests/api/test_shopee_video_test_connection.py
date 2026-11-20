"""POST /shopee-video/test-connection: ping somente leitura, sem segredos na resposta."""

import pytest
from fastapi.testclient import TestClient

from api import shopee_video_tokens as tokens
from api.main import app
from api.routers import shopee_video
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id
from apis.shopee_video import ShopeeVideoRejected, ShopeeVideoTransportError

SECRETS = ("tok-access-fake", "key-partner-fake", "98765")


class FakeClient:
    """Substitui ShopeeVideoClient: nenhuma chamada de rede real."""

    outcome = {"response": {"video_list": [{"video_id": "v1"}], "total": 1}}
    paths = []

    def __init__(self, authorization, *, sandbox, enabled):
        self.host = "https://partner.test-stable.shopeemobile.com"

    def get_video_list(self, *, page_no, page_size):
        FakeClient.paths.append((page_no, page_size))
        outcome = FakeClient.outcome
        if isinstance(outcome, Exception):
            raise outcome
        return outcome["response"]


@pytest.fixture
def ping(monkeypatch):
    auth = tokens.ValidAuthorization(123, "key-partner-fake", 98765, "tok-access-fake", True)
    logged = []
    FakeClient.paths = []
    FakeClient.outcome = {"response": {"video_list": [{"video_id": "v1"}], "total": 1}}
    monkeypatch.setattr(tokens, "get_valid_authorization", lambda *_a, **_k: auth)
    monkeypatch.setattr(shopee_video, "ShopeeVideoClient", FakeClient)
    def _strict_log_action(action, message=None, *, user_id=None, username=None, profile_id=None, force=False):
        # Mesma assinatura de api.audit_log.log_action: argumento extra (ex.: ok=) vira TypeError.
        logged.append((action, message))

    monkeypatch.setattr(shopee_video, "log_action", _strict_log_action)
    app.dependency_overrides[get_current_user_id] = lambda: "owner"
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app, base_url="https://testserver"), logged
    app.dependency_overrides.clear()


def _assert_no_secrets(response):
    for secret in SECRETS:
        assert secret not in response.text


def test_success_returns_only_counts_and_keys(ping):
    client, logged = ping
    response = client.post("/shopee-video/test-connection")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "ok": True, "http_reachable": True, "videos_returned": 1,
        "response_keys": ["total", "video_list"], "sandbox": True,
        "host": "partner.test-stable.shopeemobile.com",
    }
    assert FakeClient.paths == [(1, 1)]
    assert logged[0] == ("shopee_video_test_connection", "ok=True")
    _assert_no_secrets(response)


def test_shopee_rejection_is_reported_truncated(ping):
    client, logged = ping
    FakeClient.outcome = ShopeeVideoRejected(
        "recusou", code="error_auth", detail="m" * 500, request_id="req-1",
    )
    response = client.post("/shopee-video/test-connection")
    body = response.json()
    assert response.status_code == 200
    assert body == {"ok": False, "http_reachable": True, "shopee_error": "error_auth",
                    "shopee_message": "m" * 200, "request_id": "req-1"}
    assert logged[0] == ("shopee_video_test_connection", "ok=False")
    _assert_no_secrets(response)


def test_network_failure_is_http_200_unreachable(ping):
    client, _ = ping
    FakeClient.outcome = ShopeeVideoTransportError("sem rede")
    response = client.post("/shopee-video/test-connection")
    assert response.status_code == 200
    assert response.json() == {"ok": False, "http_reachable": False,
                               "error": "Falha de comunicação com a Shopee"}
    _assert_no_secrets(response)


def test_timeout_is_reported_as_unreachable(ping, monkeypatch):
    client, _ = ping
    monkeypatch.setattr(shopee_video, "PING_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(shopee_video, "_ping_video_list",
                        lambda _auth: __import__("time").sleep(0.5))
    response = client.post("/shopee-video/test-connection")
    assert response.status_code == 200 and response.json()["http_reachable"] is False


def test_without_connection_returns_409(ping, monkeypatch):
    client, _ = ping

    def reconnect(*_a, **_k):
        raise tokens.ShopeeVideoReconnectRequired(tokens.RECONNECT_MESSAGE)

    monkeypatch.setattr(tokens, "get_valid_authorization", reconnect)
    response = client.post("/shopee-video/test-connection")
    assert response.status_code == 409 and "reconecte" in response.json()["detail"]


def test_without_configuration_returns_503(ping, monkeypatch):
    client, _ = ping

    def missing(*_a, **_k):
        raise tokens.ShopeeVideoNotConfigured(tokens.NOT_CONFIGURED_MESSAGE)

    monkeypatch.setattr(tokens, "get_valid_authorization", missing)
    response = client.post("/shopee-video/test-connection")
    assert response.status_code == 503 and "configurada" in response.json()["detail"]
