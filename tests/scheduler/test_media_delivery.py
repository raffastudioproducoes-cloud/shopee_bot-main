"""URL de entrega da mídia para a Meta: storage:// vira URL assinada
(sem Cloudinary); caminho local legado continua indo pelo Cloudinary."""

import pytest

from shopee_bot.scheduler import media_delivery
from meta_fakes import FakeStorage


def test_storage_media_gets_signed_url_without_cloudinary(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr(media_delivery, "_storage", lambda: storage)
    monkeypatch.setattr(
        media_delivery, "_upload_legacy",
        lambda media: pytest.fail("durável não pode passar pelo Cloudinary"),
    )

    url, cleanup = media_delivery.delivery_url(
        {"type": "IMAGE", "file_path": "storage://post-media/drafts/1/p/a.jpg"}
    )

    assert url == "https://signed.example/post-media/drafts/1/p/a.jpg?token=t"
    assert storage.signed == [("post-media", "drafts/1/p/a.jpg", media_delivery.SIGNED_URL_TTL)]
    cleanup()  # nada a limpar


def test_legacy_media_uploads_to_cloudinary_and_cleans_up(monkeypatch):
    destroyed = []
    monkeypatch.setattr(
        media_delivery, "_upload_legacy",
        lambda media: ("https://cdn.example/a.jpg", lambda: destroyed.append("a")),
    )
    monkeypatch.setattr(media_delivery, "_storage", lambda: pytest.fail("legado não usa Storage"))

    url, cleanup = media_delivery.delivery_url({"type": "IMAGE", "file_path": "web/media/7/a.jpg"})

    assert url == "https://cdn.example/a.jpg"
    assert destroyed == []
    cleanup()
    assert destroyed == ["a"]


def test_malformed_storage_reference_is_rejected():
    with pytest.raises(ValueError):
        media_delivery.delivery_url({"type": "IMAGE", "file_path": "storage://sem-chave"})
