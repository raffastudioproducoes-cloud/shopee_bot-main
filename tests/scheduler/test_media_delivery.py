"""URL de entrega da mídia para a Meta: somente Supabase Storage privado."""

import os

import pytest
import requests

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


# --- local_file: mídia do Storage como arquivo local (TikTok) -------------

class _FakeStream:
    def __init__(self, chunks, status_code=200):
        self._chunks, self.status_code = chunks, status_code

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, size):
        yield from self._chunks


def _patch_download(monkeypatch, stream=None, error=None):
    monkeypatch.setattr(media_delivery, "_storage", lambda: FakeStorage())
    urls = []

    def fake_get(url, stream=False, timeout=None):
        urls.append(url)
        if error:
            raise error
        return globals()["_STREAM"]

    globals()["_STREAM"] = stream
    monkeypatch.setattr(media_delivery.requests, "get", fake_get)
    return urls


VIDEO = {"type": "VIDEO", "file_path": "storage://post-media/drafts/1/p/a.mp4"}


def test_local_file_downloads_to_temp_and_removes_it(monkeypatch):
    urls = _patch_download(monkeypatch, _FakeStream([b"abc", b"def"]))
    with media_delivery.local_file(VIDEO, 100) as path:
        assert path.endswith(".mp4")
        with open(path, "rb") as f:
            assert f.read() == b"abcdef"
    assert urls == ["https://signed.example/post-media/drafts/1/p/a.mp4?token=t"]
    assert not os.path.exists(path)


def test_local_file_removes_temp_when_body_fails(monkeypatch):
    _patch_download(monkeypatch, _FakeStream([b"abc"]))
    with pytest.raises(RuntimeError):
        with media_delivery.local_file(VIDEO, 100) as path:
            raise RuntimeError("falha na publicação")
    assert not os.path.exists(path)


def test_local_file_rejects_oversized_media(monkeypatch):
    _patch_download(monkeypatch, _FakeStream([b"abcd", b"efgh"]))
    with pytest.raises(media_delivery.MediaDownloadError, match="tamanho máximo"):
        with media_delivery.local_file(VIDEO, 5):
            pytest.fail("não deveria entrar")


def test_local_file_http_error_is_clean(monkeypatch):
    _patch_download(monkeypatch, _FakeStream([], status_code=404))
    with pytest.raises(media_delivery.MediaDownloadError, match="HTTP 404"):
        with media_delivery.local_file(VIDEO, 100):
            pytest.fail("não deveria entrar")


def test_local_file_network_error_hides_signed_url(monkeypatch):
    _patch_download(monkeypatch, error=requests.ConnectionError(
        "falha em https://signed.example/post-media/drafts/1/p/a.mp4?token=t"))
    with pytest.raises(media_delivery.MediaDownloadError) as info:
        with media_delivery.local_file(VIDEO, 100):
            pytest.fail("não deveria entrar")
    assert "token=" not in str(info.value) and "signed.example" not in str(info.value)


def test_local_file_legacy_path_becomes_media_error(monkeypatch):
    monkeypatch.setattr(media_delivery, "_storage", lambda: pytest.fail("legado não consulta Storage"))
    with pytest.raises(media_delivery.MediaDownloadError, match="Reenvie a mídia"):
        with media_delivery.local_file({"file_path": "web/media/7/a.mp4"}, 100):
            pytest.fail("não deveria entrar")
