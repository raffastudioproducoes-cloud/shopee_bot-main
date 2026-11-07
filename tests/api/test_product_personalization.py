"""Contrato de personalização de produtos e galeria privada.

Usa apenas fakes já existentes; não cria ambiente Supabase de teste.
"""
import asyncio
from io import BytesIO
from types import SimpleNamespace
from contextlib import nullcontext

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from api.main import app
from api.routers.auth import get_current_user_id
from api.routers.products import ProductUpdate
from api.routers import product_media as product_media_module
from api.routers import products as products_module


@pytest.mark.parametrize("field", [
    "product_id", "original_link", "commission_link", "commission",
    "image", "price_min", "price_max", "category",
])
def test_product_update_rejects_commercial_fields(field):
    with pytest.raises(ValidationError):
        ProductUpdate.model_validate({"name": "Seguro", field: "123"})


@pytest.mark.parametrize("description", [
    "Visite https://shopee.com.br/item/1",
    "www.exemplo.com oferta",
    "Veja s.shopee.com.br/abc",
    "https://s.shopee.com.br/abc",
    "🙂" * 141,  # caracteres ponderados X > 280
])
def test_product_description_rejects_url_and_long_copy(description):
    with pytest.raises(ValidationError):
        ProductUpdate.model_validate({"description": description})


def test_product_update_accepts_short_text_without_links():
    data = ProductUpdate.model_validate({"name": "Kit quarto", "description": "Conforto para o quarto."})
    assert data.model_dump(exclude_unset=True) == {
        "name": "Kit quarto", "description": "Conforto para o quarto."
    }


def test_product_update_rejects_null_name():
    with pytest.raises(ValidationError):
        ProductUpdate.model_validate({"name": None})


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (3, 3), "blue").save(buffer, format="JPEG")
    return buffer.getvalue()


class StorageFake:
    def __init__(self):
        self.uploads = []
        self.removals = []

    def from_(self, bucket):
        assert bucket == "post-media"
        return self

    def upload(self, key, data, opts):
        self.uploads.append((key, data, opts))

    def create_signed_url(self, key, seconds):
        assert seconds == 900
        return {"signedURL": "https://storage.invalid/private?id=opaque"}

    def remove(self, keys):
        self.removals.append(keys)


def _client(fake_db, monkeypatch, medias=None):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    db = fake_db({
        "products": [{"id": 7, "user_id": 42, "name": "Produto", "image": "https://cf.shopee.com.br/img"}],
        "product_media": medias or [],
    })
    db.storage = StorageFake()
    monkeypatch.setattr(product_media_module, "supabase", db)
    monkeypatch.setattr(products_module, "supabase", db)
    monkeypatch.setattr(product_media_module, "storage_upload_reservation", lambda size: nullcontext())
    return TestClient(app), db


def test_media_upload_is_private_scoped_and_persistent(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    result = client.post("/products/7/media", files={"file": ("foto.jpg", _jpeg(), "image/jpeg")})
    assert result.status_code == 201, result.text
    assert result.json()["media_type"] == "IMAGE"
    assert "storage_key" not in result.json()
    row = db.tables["product_media"][0]
    assert row["storage_key"].startswith("products/42/7/")
    assert row["status"] == "ready"
    assert len(db.storage.uploads) == 1
    assert result.json()["preview_url"].startswith("https://")


def test_media_limits_for_each_type(fake_db, monkeypatch):
    medias = [
        {"id": str(i), "user_id": 42, "product_id": 7, "media_type": "IMAGE", "slot": i, "status": "ready"}
        for i in range(1, 6)
    ]
    client, db = _client(fake_db, monkeypatch, medias)
    result = client.post("/products/7/media", files={"file": ("foto.jpg", _jpeg(), "image/jpeg")})
    assert result.status_code == 409
    assert not db.storage.uploads


def test_media_from_other_account_is_invisible(fake_db, monkeypatch):
    row = {
        "id": "88888888-8888-4888-8888-888888888888",
        "user_id": 99, "product_id": 7, "media_type": "IMAGE", "slot": 1,
        "storage_key": "products/99/7/photo.jpg", "status": "ready",
    }
    client, db = _client(fake_db, monkeypatch, [row])
    listing = client.get("/products/7/media")
    assert listing.status_code == 200
    assert listing.json()["items"] == []
    res = client.delete("/products/7/media/" + row["id"])
    assert res.status_code == 404
    assert not db.storage.removals


def test_media_rejects_product_not_owned_by_account(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    response = client.get("/products/777/media")
    assert response.status_code == 404
    assert not db.storage.uploads


def test_upload_rejects_non_media(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    res = client.post("/products/7/media", files={"file": ("shell.txt", b"not image", "text/plain")})
    assert res.status_code in (400, 415)
    assert not db.storage.uploads


def test_media_route_requires_login():
    app.dependency_overrides.clear()
    client = TestClient(app)
    assert client.get("/products/7/media").status_code == 401
    assert client.post("/products/7/media", files={"file": ("a.jpg", _jpeg(), "image/jpeg")}).status_code == 401


def test_short_description_reuses_persona_without_commercial_links():
    from api.text_variants import generate_short_product_description
    from api.network_limits import NETWORK_RULES, text_length

    seen = []
    def complete(prompt, max_tokens):
        seen.append((prompt, max_tokens))
        return "Descrição: A Lavadora portátil é prática para a rotina. https://s.shopee.com.br/exemplo"

    text = generate_short_product_description({"name": "Lavadora portátil", "commission_link": "https://secret.invalid"}, "casual", complete)
    assert text == "A Lavadora portátil é prática para a rotina."
    assert "https" not in text
    assert "secret.invalid" not in seen[0][0]
    assert "Lavadora portátil" in seen[0][0]
    assert text_length(NETWORK_RULES["x"], text) <= 280


def test_short_description_limits_weighted_emoji_without_cutting_unicode():
    from api.text_variants import generate_short_product_description
    from api.network_limits import NETWORK_RULES, text_length

    text = generate_short_product_description(
        {"name": "Produto"},
        "divertido",
        lambda prompt, max_tokens: "Ótimo produto! " + "😀" * 200,
    )
    assert text_length(NETWORK_RULES["x"], text) <= 280


def test_short_description_generation_payload_isolated_from_post_variants():
    from api.routers.posts import GenerateCopyBody
    parsed = GenerateCopyBody.model_validate({
        "product_id": 7, "persona": "profissional", "description_only": True, "provider": "gemini",
    })
    assert parsed.description_only is True
    with pytest.raises(ValidationError):
        GenerateCopyBody.model_validate({
            "product_id": 7, "description_only": True, "networks": ["threads"],
        })


def test_product_description_endpoint_uses_existing_gemini_and_does_not_write(fake_db, monkeypatch):
    from api.routers import posts as posts_module
    from api.routers import platform_ai as platform_ai_module
    from apis import llm

    client, db = _client(fake_db, monkeypatch)
    monkeypatch.setattr(posts_module, "supabase", db)
    monkeypatch.setattr(posts_module, "_check_login_rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(platform_ai_module, "resolve_platform_ai_key", lambda: ("gemini", "fixture-only", "gemini-test"))
    monkeypatch.setattr(llm, "complete", lambda provider, key, model, prompt, max_tokens: "Uma peça prática para o dia a dia.")
    response = client.post("/posts/generate-copy", json={
        "product_id": 7, "persona": "casual", "description_only": True, "provider": "gemini",
    })
    assert response.status_code == 200, response.text
    assert response.json()["text"] == "Uma peça prática para o dia a dia."
    assert response.json()["parts"] == ["Uma peça prática para o dia a dia."]
    assert response.json()["variants"] == []
    assert db.tables["products"][0]["name"] == "Produto"

    missing = client.post("/posts/generate-copy", json={
        "product_id": 999, "description_only": True, "provider": "gemini",
    })
    assert missing.status_code == 404


def test_update_product_accepts_update_builder_without_single(monkeypatch):
    """Regressão do 500: SyncFilterRequestBuilder após UPDATE não tem .single()."""
    saved = {
        "id": 7, "user_id": 42, "name": "Antes", "description": None,
        "commission": 33, "image": "https://cf.shopee.com.br/img",
    }
    observed = {}

    class UpdateQuery:
        def __init__(self, fields):
            self.fields = fields
            self.filters = {}

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def execute(self):
            observed["filters"] = dict(self.filters)
            if any(saved.get(key) != value for key, value in self.filters.items()):
                return SimpleNamespace(data=[])
            saved.update(self.fields)
            return SimpleNamespace(data=[dict(saved)])

    class FakeTable:
        def update(self, fields):
            return UpdateQuery(fields)

    class FakeDB:
        def table(self, name):
            assert name == "products"
            return FakeTable()

    monkeypatch.setattr(products_module, "_get", lambda user_id, product_id: dict(saved))
    monkeypatch.setattr(products_module, "supabase", FakeDB())
    monkeypatch.setattr(products_module, "scope_account", lambda q, uid: q.eq("user_id", uid))

    body = ProductUpdate(name="Depois", description="Descrição curta, sem link.")
    updated = asyncio.run(products_module.update_product(7, body, user_id=42))
    assert updated["name"] == "Depois"
    assert updated["description"] == "Descrição curta, sem link."
    assert saved["commission"] == 33
    assert saved["image"] == "https://cf.shopee.com.br/img"
    assert observed["filters"] == {"id": 7, "user_id": 42}

    # O UPDATE não pode alcançar outra conta, mesmo se a checagem inicial falhar.
    with pytest.raises(HTTPException) as error:
        asyncio.run(products_module.update_product(7, ProductUpdate(name="Intruso"), user_id=99))
    assert error.value.status_code == 404
    assert saved["name"] == "Depois"
