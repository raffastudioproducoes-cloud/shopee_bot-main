"""Host único da API Shopee Vídeo (cliente e OAuth) e proteção contra SSRF."""

import pytest

from apis import shopee_video_host as host


def test_defaults_are_partner_hosts(monkeypatch):
    monkeypatch.delenv("SHOPEE_VIDEO_API_BASE_URL", raising=False)
    monkeypatch.delenv("SHOPEE_VIDEO_SANDBOX_API_BASE_URL", raising=False)
    assert host.api_base_url(sandbox=False) == "https://openplatform.shopee.com.br"
    assert host.api_base_url(sandbox=True) == "https://partner.test-stable.shopeemobile.com"


@pytest.mark.parametrize("value", [
    "https://openplatform.shopee.com.br",
    "https://partner.shopeemobile.com/",
    "https://openplatform.sandbox.test-stable.shopee.sg",
    "https://partner.shopee.com",
])
def test_env_override_accepts_shopee_domains(monkeypatch, value):
    monkeypatch.setenv("SHOPEE_VIDEO_API_BASE_URL", value)
    assert host.api_base_url(sandbox=False) == value.rstrip("/")


@pytest.mark.parametrize("value", [
    "http://partner.shopeemobile.com",
    "https://evil.example.com",
    "https://shopeemobile.com.evil.io",
    "https://evilshopee.com.br",
    "https://user@partner.shopeemobile.com",
    "https://partner.shopeemobile.com:8443",
    "https://partner.shopeemobile.com/api",
    "https://partner.shopeemobile.com?x=1",
    "ftp://partner.shopeemobile.com",
])
def test_env_override_rejects_unsafe_hosts(monkeypatch, value):
    monkeypatch.setenv("SHOPEE_VIDEO_SANDBOX_API_BASE_URL", value)
    with pytest.raises(ValueError):
        host.api_base_url(sandbox=True)


def test_client_and_oauth_share_the_same_host(monkeypatch):
    from api import shopee_video_oauth as oauth
    from apis import shopee_video as sv

    monkeypatch.setenv("SHOPEE_VIDEO_API_BASE_URL", "https://openplatform.shopee.com.br")
    auth = sv.ShopeeVideoAuthorization(1, "k" * 8, 2, "t", permission_granted=True)
    client = sv.ShopeeVideoClient(auth, sandbox=False, enabled=True, session=object())
    assert client.host == oauth.api_host(sandbox=False) == "https://openplatform.shopee.com.br"
