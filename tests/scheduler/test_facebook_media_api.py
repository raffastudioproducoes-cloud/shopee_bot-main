"""apis/facebook.py: álbum e vídeo via Graph API, com HTTP estritamente
simulado (FakeGraph falha em qualquer rota não prevista)."""

import json

import pytest

from meta_fakes import FakeGraph, FakeResponse
import shopee_bot.apis.facebook as FacebookAPI

BASE = FacebookAPI.API_BASE


def _install(monkeypatch, routes):
    graph = FakeGraph(routes)
    monkeypatch.setattr(FacebookAPI.requests, "get", graph.get)
    monkeypatch.setattr(FacebookAPI.requests, "post", graph.post)
    return graph


def test_album_uploads_unpublished_photos_then_attaches_them_to_one_feed_post(monkeypatch):
    graph = _install(monkeypatch, {
        ("POST", f"{BASE}/page-1/photos"): [{"id": "ph-1"}, {"id": "ph-2"}],
        ("POST", f"{BASE}/page-1/feed"): [{"id": "page-1_post-9"}],
    })

    result = FacebookAPI.post_album_as_page(
        "tok", "page-1", ["https://u/1.jpg", "https://u/2.jpg"], "legenda"
    )

    assert result == {"id": "page-1_post-9"}
    photo_calls = [c for c in graph.calls if c["url"].endswith("/photos")]
    assert [c["params"]["url"] for c in photo_calls] == ["https://u/1.jpg", "https://u/2.jpg"]
    assert all(c["params"]["published"] == "false" for c in photo_calls)
    feed = graph.calls[-1]["params"]
    assert feed["message"] == "legenda"
    assert json.loads(feed["attached_media[0]"]) == {"media_fbid": "ph-1"}
    assert json.loads(feed["attached_media[1]"]) == {"media_fbid": "ph-2"}


def test_album_does_not_publish_feed_post_when_a_photo_fails(monkeypatch):
    graph = _install(monkeypatch, {
        ("POST", f"{BASE}/page-1/photos"): [{"id": "ph-1"}, FakeResponse({"error": {}}, 400)],
    })

    with pytest.raises(Exception, match="imagem 2"):
        FacebookAPI.post_album_as_page("tok", "page-1", ["https://u/1.jpg", "https://u/2.jpg"], "x")

    assert f"{BASE}/page-1/feed" not in graph.urls("POST")
