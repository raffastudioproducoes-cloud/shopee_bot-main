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
