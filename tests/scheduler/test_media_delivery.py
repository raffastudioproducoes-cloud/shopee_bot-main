"""URL de entrega da mídia para a Meta: somente Supabase Storage privado."""

import pytest

from shopee_bot.scheduler import media_delivery
from meta_fakes import FakeStorage


def test_storage_media_gets_signed_url(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr(media_delivery, "_storage", lambda: storage)
    url, cleanup = media_delivery.delivery_url(
        {"type": "IMAGE", "file_path": "storage://post-media/drafts/1/p/a.jpg"}
    )

    assert url == "https://signed.example/post-media/drafts/1/p/a.jpg?token=t"
    assert storage.signed == [("post-media", "drafts/1/p/a.jpg", media_delivery.SIGNED_URL_TTL)]
    cleanup()  # nada a limpar


def test_legacy_media_is_rejected_without_external_upload(monkeypatch):
    monkeypatch.setattr(media_delivery, "_storage", lambda: pytest.fail("legado não deve consultar Storage"))
    with pytest.raises(FileNotFoundError, match="Reenvie a mídia"):
        media_delivery.delivery_url({"type": "IMAGE", "file_path": "web/media/7/a.jpg"})


def test_malformed_storage_reference_is_rejected():
    with pytest.raises(ValueError):
        media_delivery.delivery_url({"type": "IMAGE", "file_path": "storage://sem-chave"})
