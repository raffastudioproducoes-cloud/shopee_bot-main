"""apis/instagram.py: container, polling e publicação com HTTP estrito."""

import json

import pytest

from meta_fakes import FakeGraph, FakeResponse
import shopee_bot.apis.instagram as InstagramAPI

BASE = InstagramAPI.API_BASE
IG = "ig-1"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(InstagramAPI.time, "sleep", lambda seconds: None)


def _install(monkeypatch, routes):
    routes = {
        ("GET", f"{BASE}/oauth/access_token"): [{"access_token": "app-token"}],
        **routes,
    }
    graph = FakeGraph(routes)
    monkeypatch.setattr(InstagramAPI.requests, "get", graph.get)
    monkeypatch.setattr(InstagramAPI.requests, "post", graph.post)
    return graph


def _post_image():
    return InstagramAPI.post_image("app-x", "secret-x", "tok", "https://u/a.jpg", "legenda", IG)


def test_image_publishes_once_container_is_finished(monkeypatch):
    graph = _install(monkeypatch, {
        ("POST", f"{BASE}/{IG}/media"): [{"id": "c-1"}],
        ("GET", f"{BASE}/c-1"): [{"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}],
        ("POST", f"{BASE}/{IG}/media_publish"): [{"id": "m-1"}],
    })

    assert _post_image() == "m-1"
    assert graph.calls[-1]["params"]["creation_id"] == "c-1"


@pytest.mark.parametrize("status", ["ERROR", "EXPIRED"])
def test_container_failure_states_stop_polling(monkeypatch, status):
    graph = _install(monkeypatch, {
        ("POST", f"{BASE}/{IG}/media"): [{"id": "c-1"}],
        ("GET", f"{BASE}/c-1"): [{"status_code": status}],
    })

    with pytest.raises(Exception, match=status):
        _post_image()

    assert f"{BASE}/{IG}/media_publish" not in graph.urls("POST")


def test_polling_gives_up_instead_of_looping_forever(monkeypatch):
    _install(monkeypatch, {
        ("POST", f"{BASE}/{IG}/media"): [{"id": "c-1"}],
        ("GET", f"{BASE}/c-1"): [{"status_code": "IN_PROGRESS"}],
    })

    with pytest.raises(Exception, match="tempo"):
        _post_image()


def test_video_is_published_as_reels_after_container_finishes(monkeypatch):
    graph = _install(monkeypatch, {
        ("POST", f"{BASE}/{IG}/media"): [{"id": "c-v"}],
        ("GET", f"{BASE}/c-v"): [{"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}],
        ("POST", f"{BASE}/{IG}/media_publish"): [{"id": "m-v"}],
    })

    media_id = InstagramAPI.post_video("app-x", "secret-x", "tok", "https://u/v.mp4", "legenda", IG)

    assert media_id == "m-v"
    create = next(c for c in graph.calls if c["url"] == f"{BASE}/{IG}/media")["params"]
    assert create["media_type"] == "REELS"
    assert create["video_url"] == "https://u/v.mp4"
    assert create["caption"] == "legenda"
    assert "image_url" not in create


def test_video_waits_longer_than_image(monkeypatch):
    _install(monkeypatch, {
        ("POST", f"{BASE}/{IG}/media"): [{"id": "c-v"}],
        ("GET", f"{BASE}/c-v"): [{"status_code": "IN_PROGRESS"}] * 100 + [{"status_code": "FINISHED"}],
        ("POST", f"{BASE}/{IG}/media_publish"): [{"id": "m-v"}],
    })

    assert InstagramAPI.post_video("app-x", "secret-x", "tok", "https://u/v.mp4", "c", IG) == "m-v"
