"""Testes de roteamento da publicação Facebook com mídia, sem rede ou banco."""

import sys

import shopee_bot.scheduler.bot_post_facebook  # noqa: F401
from shopee_bot.database.activity_types import ActivityType

module = sys.modules["shopee_bot.scheduler.bot_post_facebook"]


def _patch_common(monkeypatch, root_post):
    monkeypatch.setattr(
        module.schedulers, "get_by_id",
        lambda job_id: {"user_id": 42, "post_id": 7, "profile_id": "profile-1"},
    )
    monkeypatch.setattr(
        module.facebook_credentials, "get_by_user_id",
        lambda user_id, profile_id=None: {
            "username": "fulano",
            "facebook_app_id": "app-1",
            "facebook_secret": "secret-1",
            "facebook_page_id": "page-1",
            "facebook_page_access_token": "page-token-1",
        },
    )
    monkeypatch.setattr(
        module.posts, "get", lambda user_id, post_id, profile_id: [root_post],
    )


def test_bot_post_facebook_with_image_uses_page_token(monkeypatch):
    image = {"type": "IMAGE", "file_path": "web/media/7/image.jpg"}
    _patch_common(monkeypatch, {"text": "foto", "product_ids": [], "medias": [image]})

    calls = {}
    monkeypatch.setattr(
        module,
        "_publish_image",
        lambda token, page_id, media, caption: calls.update(
            args=(token, page_id, media, caption)
        ),
    )
    activities = []
    monkeypatch.setattr(
        module,
        "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata, profile_id)
        ),
    )

    module.bot_post_facebook("job-image")

    assert calls["args"] == ("page-token-1", "page-1", image, "foto")
    assert activities[0][1] == ActivityType.BOT_POST_SUCCESS
    assert activities[0][3] == "profile-1"


class _PhotoRecorder:
    def __init__(self):
        self.calls = []

    def post_photo_as_page(self, page_access_token, page_id, image_url, caption):
        self.calls.append((page_access_token, page_id, image_url, caption))
        return {"id": "photo-1"}


def test_publish_image_uses_delivery_url_and_cleans_up(monkeypatch):
    cleaned = []
    monkeypatch.setattr(
        module, "delivery_url",
        lambda media: ("https://signed.example/a.jpg", lambda: cleaned.append(media["file_path"])),
    )
    recorder = _PhotoRecorder()
    monkeypatch.setattr(module.FacebookAPI, "post_photo_as_page", recorder.post_photo_as_page)

    module._publish_image("tok", "page-1", {"type": "IMAGE", "file_path": "storage://post-media/k.jpg"}, "legenda")

    assert recorder.calls == [("tok", "page-1", "https://signed.example/a.jpg", "legenda")]
    assert cleaned == ["storage://post-media/k.jpg"]


def test_publish_image_cleans_up_when_graph_fails(monkeypatch):
    cleaned = []
    monkeypatch.setattr(module, "delivery_url", lambda media: ("https://u", lambda: cleaned.append(1)))

    def boom(*args):
        raise RuntimeError("graph")

    monkeypatch.setattr(module.FacebookAPI, "post_photo_as_page", boom)

    try:
        module._publish_image("tok", "page-1", {"type": "IMAGE", "file_path": "x"}, "c")
    except RuntimeError:
        pass
    assert cleaned == [1]


def _media(name, kind="IMAGE"):
    return {"type": kind, "file_name": name, "file_path": f"storage://post-media/{name}"}


def _capture_activities(monkeypatch):
    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append((activity_type, metadata)),
    )
    return activities


def test_bot_post_facebook_with_several_images_publishes_album(monkeypatch):
    medias = [_media("a.jpg"), _media("b.png")]
    _patch_common(monkeypatch, {"text": "álbum", "product_ids": [], "medias": medias})
    calls = {}
    monkeypatch.setattr(
        module, "_publish_album",
        lambda token, page_id, items, caption: calls.update(args=(token, page_id, items, caption)),
    )
    activities = _capture_activities(monkeypatch)

    module.bot_post_facebook("job-album")

    assert calls["args"] == ("page-token-1", "page-1", medias, "álbum")
    assert activities[0][0] == ActivityType.BOT_POST_SUCCESS


def test_publish_album_resolves_every_url_and_cleans_up_all(monkeypatch):
    cleaned = []
    monkeypatch.setattr(
        module, "delivery_url",
        lambda media: (f"https://signed/{media['file_name']}", lambda: cleaned.append(media["file_name"])),
    )
    seen = {}
    monkeypatch.setattr(
        module.FacebookAPI, "post_album_as_page",
        lambda token, page_id, urls, caption: seen.update(args=(token, page_id, urls, caption)),
    )

    module._publish_album("tok", "page-1", [_media("a.jpg"), _media("b.jpg")], "c")

    assert seen["args"] == ("tok", "page-1", ["https://signed/a.jpg", "https://signed/b.jpg"], "c")
    assert cleaned == ["a.jpg", "b.jpg"]


def test_album_refuses_video_or_gif_instead_of_dropping_files(monkeypatch):
    _patch_common(monkeypatch, {
        "text": "x", "product_ids": [],
        "medias": [_media("a.jpg"), _media("b.gif")],
    })
    monkeypatch.setattr(module, "_publish_album", lambda *a: (_ for _ in ()).throw(AssertionError("não publicar")))
    activities = _capture_activities(monkeypatch)

    module.bot_post_facebook("job-gif")

    assert activities[0][0] == ActivityType.BOT_POST_FAILURE
    assert "álbum" in activities[0][1]["metadata"]["error"]
