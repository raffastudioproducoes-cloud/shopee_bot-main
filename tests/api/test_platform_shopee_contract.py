"""Shopee da plataforma: credencial global e atribuição por conta, sem vazamento."""

from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from api.crypto import decrypt, encrypt
from api.main import app
from api.routers import catalog, credentials, platform_ai, platform_shopee, posts
from api.routers.auth import get_current_user_id
from api.shopee_affiliate_links import (
    affiliate_id_from_link, build_affiliate_link, personalize_product,
)


@pytest.fixture
def shopee_db(fake_db, monkeypatch):
    db = fake_db({
        "users": [{"id": 7, "access": "ADMIN"}, {"id": 42, "access": "USER"},
                  {"id": 43, "access": "USER"}],
        "platform_shopee_credentials": [
            {"environment": "production", "app_id": "owner-app", "secret": encrypt("owner-secret"),
             "status": True, "check_state": None, "checked_at": None},
            {"environment": "staging", "app_id": "staging-app", "secret": encrypt("staging-secret"),
             "status": True, "check_state": None, "checked_at": None},
        ],
        "shopee_affiliate_accounts": [
            {"user_id": 42, "affiliate_id": "12345678901"},
            {"user_id": 43, "affiliate_id": "98765432109"},
        ],
    })
    for module in (catalog, credentials, platform_shopee):
        monkeypatch.setattr(module, "supabase", db)
    monkeypatch.setattr(platform_shopee, "log_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(platform_shopee, "current_environment", lambda: "production")
    yield db
    app.dependency_overrides.clear()


def client_for(user_id):
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app)


def test_each_user_gets_their_own_link_with_one_platform_api(shopee_db, monkeypatch):
    api_calls = []

    async def search(app_id, secret, **_):
        api_calls.append((app_id, secret))
        return [{"itemId": 123, "productName": "Produto", "priceMin": "10.00",
                 "productLink": "https://shopee.com.br/item-123?utm_source=an_OWNER",
                 "offerLink": "https://s.shopee.com.br/OWNER_LINK"}]

    monkeypatch.setattr(catalog.shopee_catalog, "search_products", search)
    links = []
    for user_id in (42, 43):
        response = client_for(user_id).get("/products/catalog-search")
        assert response.status_code == 200, response.text
        assert "OWNER_LINK" not in response.text
        links.append(response.json()["data"][0]["commission_link"])
    assert api_calls == [("owner-app", "owner-secret")] * 2
    assert [parse_qs(urlsplit(url).query)["affiliate_id"][0] for url in links] == [
        "12345678901", "98765432109",
    ]
    assert links[0] != links[1]


def test_client_only_sees_id_not_global_secret(shopee_db):
    response = client_for(42).get("/shopee/affiliate")
    assert response.status_code == 200
    assert response.json() == {"connected": True, "affiliate_id": "12345678901", "catalog_available": True}
    assert "owner-secret" not in response.text and "owner-app" not in response.text


def test_user_cannot_manage_global_key(shopee_db):
    user = client_for(42)
    assert user.get("/admin/shopee").status_code == 403
    assert user.put("/admin/shopee", json={"app_id": "attack", "secret": "attack"}).status_code == 403
    assert user.delete("/admin/shopee").status_code == 403
    assert user.post("/admin/shopee/test").status_code == 403
    assert decrypt(shopee_db.tables["platform_shopee_credentials"][0]["secret"]) == "owner-secret"


def test_affiliate_id_is_account_scoped_and_input_is_restricted(shopee_db):
    user = client_for(42)
    assert user.put("/shopee/affiliate", json={"affiliate_id": "foo"}).status_code == 400
    assert user.put("/shopee/affiliate", json={"affiliate_id": "https://evil.test/?affiliate_id=111111"}).status_code == 400
    assert user.put("/shopee/affiliate", json={"affiliate_id": "55555555555"}).status_code == 200
    assert client_for(43).get("/shopee/affiliate").json()["affiliate_id"] == "98765432109"
    assert client_for(42).delete("/shopee/affiliate").status_code == 200
    assert client_for(42).get("/shopee/affiliate").json()["connected"] is False
    assert client_for(42).get("/products/catalog-search").status_code == 400


def test_admin_can_rotate_staging_without_touching_production(shopee_db, monkeypatch):
    monkeypatch.setattr(platform_shopee, "current_environment", lambda: "staging")
    admin = client_for(7)
    response = admin.put("/admin/shopee", json={"app_id": "new-staging", "secret": "new-secret"})
    assert response.status_code == 200
    assert "new-secret" not in response.text
    rows = {r["environment"]: r for r in shopee_db.tables["platform_shopee_credentials"]}
    assert decrypt(rows["staging"]["secret"]) == "new-secret"
    assert decrypt(rows["production"]["secret"]) == "owner-secret"
    assert admin.get("/admin/shopee").json()["connected"] is True


def test_admin_tests_global_api_without_exposing_secret(shopee_db, monkeypatch):
    called = []

    async def validator(app_id, secret):
        called.append((app_id, secret))
        return True

    monkeypatch.setattr(platform_shopee, "validate_shopee_credential", validator)
    monkeypatch.setattr(platform_shopee, "_check_test_rate_limit", lambda _uid: None)
    admin = client_for(7)
    result = admin.post("/admin/shopee/test")
    assert result.status_code == 200
    assert result.json()["light"] == "green"
    assert called == [("owner-app", "owner-secret")]
    assert "owner-secret" not in result.text
    assert admin.get("/admin/shopee").json()["state"] == "ok"


def test_link_parser_and_old_saved_product_never_fall_back_to_owner():
    product = "https://shopee.com.br/product/12/34?utm_source=an_999999&sub_id=owner"
    link = build_affiliate_link(product, "12345678901")
    query = parse_qs(urlsplit(link).query)
    assert query["origin_link"] == ["https://shopee.com.br/product/12/34"]
    assert query["affiliate_id"] == ["12345678901"]
    assert affiliate_id_from_link(link) == "12345678901"
    assert affiliate_id_from_link("https://s.shopee.com.br/opaque") is None
    assert build_affiliate_link("https://evil.test/phishing", "12345678901") is None
    assert build_affiliate_link("https://shopee.com.br.evil.test/prod", "12345678901") is None
    old = {"original_link": product, "commission_link": "https://s.shopee.com.br/owner"}
    assert personalize_product(old, "98765432109")["commission_link"].endswith("affiliate_id=98765432109")
    assert personalize_product(old, None)["commission_link"] == ""
    assert old["commission_link"] == "https://s.shopee.com.br/owner"


def test_copy_generation_never_sends_legacy_owner_link_to_ai(shopee_db, monkeypatch):
    shopee_db.tables["products"] = [{"id": 5, "user_id": 42, "name": "Produto",
                                    "original_link": "https://shopee.com.br/item-5",
                                    "commission_link": "https://s.shopee.com.br/owner-link"}]
    # FakeDB stores row lists by reference on table(name); replacing the array
    # is fine here because a new _FakeTable is allocated per request.
    monkeypatch.setattr(posts, "supabase", shopee_db)
    monkeypatch.setattr(platform_ai, "resolve_platform_ai_key", lambda: ("gemini", "key", "model"))
    monkeypatch.setattr(posts, "_check_login_rate_limit", lambda *_args, **_kw: None)
    seen = []

    def generate(product, *_args):
        seen.append(product)
        return [{"text": "Texto de teste", "networks": ["threads"]}]

    monkeypatch.setattr(posts, "generate_variants", generate)
    monkeypatch.setattr(posts, "generate_thread_replies", lambda *_args: [])
    response = client_for(42).post("/posts/generate-copy", json={"product_id": 5})
    assert response.status_code == 200, response.text
    assert "affiliate_id=12345678901" in seen[0]["commission_link"]
    assert "owner-link" not in str(seen) and "owner-link" not in response.text
