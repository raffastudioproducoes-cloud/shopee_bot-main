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
    # Sem escolha gravada = vídeo comum (posts antigos).
    monkeypatch.setattr(module.posts, "get_facebook_reels", lambda *a: False)


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

    result = module.bot_post_facebook("job-image")

    assert calls["args"] == ("page-token-1", "page-1", image, "foto")
    assert result.status == "succeeded"
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


def test_bot_post_facebook_with_single_video_publishes_video(monkeypatch):
    video = _media("v.mp4", "VIDEO")
    _patch_common(monkeypatch, {"text": "clipe", "product_ids": [], "medias": [video]})
    calls = {}
    monkeypatch.setattr(
        module, "_publish_video",
        lambda token, page_id, media, caption: calls.update(args=(token, page_id, media, caption)),
    )
    activities = _capture_activities(monkeypatch)

    module.bot_post_facebook("job-video")

    assert calls["args"] == ("page-token-1", "page-1", video, "clipe")
    assert activities[0][0] == ActivityType.BOT_POST_SUCCESS


def test_publish_video_uses_delivery_url_and_cleans_up(monkeypatch):
    cleaned = []
    monkeypatch.setattr(
        module, "delivery_url", lambda media: ("https://signed/v.mp4", lambda: cleaned.append(1)),
    )
    seen = {}
    monkeypatch.setattr(
        module.FacebookAPI, "post_video_as_page",
        lambda token, page_id, url, caption: seen.update(args=(token, page_id, url, caption)),
    )

    module._publish_video("tok", "page-1", _media("v.mp4", "VIDEO"), "c")

    assert seen["args"] == ("tok", "page-1", "https://signed/v.mp4", "c")
    assert cleaned == [1]


def test_video_without_page_token_fails_instead_of_publishing_text(monkeypatch):
    _patch_common(monkeypatch, {"text": "clipe", "product_ids": [], "medias": [_media("v.mp4", "VIDEO")]})
    monkeypatch.setattr(
        module.facebook_credentials, "get_by_user_id",
        lambda user_id, profile_id=None: {
            "username": "f", "facebook_app_id": "a", "facebook_secret": "s",
            "facebook_page_id": "page-1", "facebook_page_access_token": None,
        },
    )
    monkeypatch.setattr(module.FacebookAPI, "post_text", lambda *a: (_ for _ in ()).throw(AssertionError("texto")))
    activities = _capture_activities(monkeypatch)

    module.bot_post_facebook("job-video-legacy")

    assert activities[0][0] == ActivityType.BOT_POST_FAILURE
    assert "vídeo" in activities[0][1]["metadata"]["error"]


def test_mixed_images_and_video_publishes_image_album_and_warns(monkeypatch):
    medias = [_media("a.jpg"), _media("b.jpg"), _media("c.jpg"), _media("v.mp4", "VIDEO")]
    _patch_common(monkeypatch, {"text": "mix", "product_ids": [], "medias": medias})
    calls = {}
    monkeypatch.setattr(
        module, "_publish_album",
        lambda token, page_id, items, caption: calls.update(items=items),
    )
    monkeypatch.setattr(module, "_publish_video", lambda *a: (_ for _ in ()).throw(AssertionError("vídeo")))
    warnings = []
    monkeypatch.setattr(module.logger, "warning", warnings.append)
    activities = _capture_activities(monkeypatch)

    module.bot_post_facebook("job-mix")

    assert [m["file_name"] for m in calls["items"]] == ["a.jpg", "b.jpg", "c.jpg"]
    assert activities[0][0] == ActivityType.BOT_POST_SUCCESS
    assert "v.mp4" in warnings[0]


def test_graph_error_with_media_is_logged_as_error_not_text_fallback(monkeypatch):
    medias = [_media("a.jpg"), _media("b.jpg")]
    _patch_common(monkeypatch, {"text": "x", "product_ids": [], "medias": medias})
    monkeypatch.setattr(module, "_publish_album", lambda *a: (_ for _ in ()).throw(RuntimeError("signed url")))
    monkeypatch.setattr(module.FacebookAPI, "post_text_as_page", lambda *a: (_ for _ in ()).throw(AssertionError("texto")))
    errors = []
    monkeypatch.setattr(module.logger, "exception", errors.append)
    activities = _capture_activities(monkeypatch)

    module.bot_post_facebook("job-err")

    assert activities[0][0] == ActivityType.BOT_POST_FAILURE
    assert "signed url" in errors[0]


def test_photo_publication_stores_post_id_for_metrics(monkeypatch):
    """/photos devolve id da foto e post_id; métricas por post precisam do post_id."""
    image = {"type": "IMAGE", "file_path": "web/media/7/image.jpg"}
    _patch_common(monkeypatch, {"text": "foto", "product_ids": [], "medias": [image]})
    monkeypatch.setattr(module, "_publish_image", lambda *a: {"id": "555", "post_id": "111_222"})
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)
    assert module.bot_post_facebook("job-photo").external_id == "111_222"
    monkeypatch.setattr(module, "_publish_image", lambda *a: {"id": "111_333"})
    assert module.bot_post_facebook("job-photo").external_id == "111_333"


def test_product_only_post_link_goes_through_click_redirect(monkeypatch):
    _patch_common(monkeypatch, {"text": "", "product_ids": [11], "medias": []})
    product = {"name": "Fone", "commission_link": "https://s.shopee.com.br/AbC1"}
    monkeypatch.setattr(module.products, "get", lambda user_id, product_id, profile_id: dict(product))
    monkeypatch.setattr(module, "active_publish_job_id", lambda: "job-77")
    seen = {}

    def rewrite_link(url, job_id):
        seen["args"] = (url, job_id)
        return "https://autoorbital.example/r/token-1234567890123456"
    monkeypatch.setattr(module.post_link_redirects, "rewrite_link", rewrite_link)
    sent = {}
    monkeypatch.setattr(module.FacebookAPI, "post_product_as_page",
                        lambda token, page_id, prod: sent.update(product=prod) or {"id": "1_2"})
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)

    result = module.bot_post_facebook("job-product")

    assert result.status == "succeeded"
    assert seen["args"] == ("https://s.shopee.com.br/AbC1", "job-77")
    assert sent["product"]["commission_link"] == "https://autoorbital.example/r/token-1234567890123456"
    assert product["commission_link"] == "https://s.shopee.com.br/AbC1"  # dict original intacto


def test_product_link_stays_direct_when_redirect_is_disabled(monkeypatch):
    _patch_common(monkeypatch, {"text": "", "product_ids": [11], "medias": []})
    monkeypatch.setattr(module.products, "get",
                        lambda *a: {"name": "Fone", "commission_link": "https://s.shopee.com.br/AbC1"})
    monkeypatch.delenv("CLICK_REDIRECT_BASE_URL", raising=False)
    sent = {}
    monkeypatch.setattr(module.FacebookAPI, "post_product_as_page",
                        lambda token, page_id, prod: sent.update(product=prod) or {"id": "1_2"})
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)

    assert module.bot_post_facebook("job-product").status == "succeeded"
    assert sent["product"]["commission_link"] == "https://s.shopee.com.br/AbC1"
