"""Contrato de personalização de produtos e galeria privada.

Usa apenas fakes já existentes; não cria ambiente Supabase de teste.
"""
from io import BytesIO
from contextlib import nullcontext

import pytest
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
