"""
Testes de scheduler/bot_post_instagram.py — cobre só o roteamento (qual
credencial é lida, qual função da apis/instagram.py é chamada com quais
argumentos, e o registro de atividade de sucesso/falha). Não toca banco
de verdade nem rede (tudo mockado via monkeypatch).
"""

import sys

# import (não "from X import Y") de propósito: scheduler/__init__.py faz
# "from .bot_post_instagram import bot_post_instagram", o que sobrescreve
# o atributo `bot_post_instagram` do pacote com a FUNÇÃO — pegar o
# submódulo teria que ser via sys.modules, não via atributo do pacote
# (que já não é mais o módulo depois desse import).
import shopee_bot.scheduler.bot_post_instagram  # noqa: F401
from shopee_bot.database.activity_types import ActivityType

module = sys.modules["shopee_bot.scheduler.bot_post_instagram"]


def _user_data(**overrides):
    base = {
        "username": "fulano",
        "instagram_app_id": "app-1",
        "instagram_secret": "secret-1",
        "instagram_user_access_token": "user-token-1",
        "instagram_ig_user_id": "ig-user-1",
    }
    base.update(overrides)
    return base


def _patch_common(monkeypatch, user_data, root_post):
    monkeypatch.setattr(
        module.schedulers, "get_by_id",
        lambda job_id: {"user_id": 42, "post_id": 7, "profile_id": "profile-1"},
    )
    monkeypatch.setattr(
        module.instagram_credentials, "get_by_user_id",
        lambda user_id, profile_id=None: user_data,
    )
    monkeypatch.setattr(
        module.posts, "get", lambda user_id, post_id, profile_id: [root_post],
    )


def test_bot_post_instagram_text_only_uses_saved_token_and_ig_user_id(monkeypatch):
    user_data = _user_data()
    root_post = {"text": "oi", "product_ids": []}
    _patch_common(monkeypatch, user_data, root_post)

    calls = {}

    def fake_post_text(app_id, secret, user_access_token, text, ig_user_id):
        calls["args"] = (app_id, secret, user_access_token, text, ig_user_id)
        return "media-1"

    monkeypatch.setattr(module.InstagramAPI, "post_text", fake_post_text)

    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata)
        ),
    )

    module.bot_post_instagram("job-1")

    assert calls["args"] == (
        "app-1", "secret-1", "user-token-1", "oi", "ig-user-1"
    )
    assert len(activities) == 1
    user_id, activity_type, metadata = activities[0]
    assert user_id == 42
    assert activity_type == ActivityType.BOT_POST_SUCCESS
    assert metadata["metadata"]["post_id"] == 7


def test_bot_post_instagram_with_product_calls_post_product(monkeypatch):
    user_data = _user_data()
    root_post = {"text": "", "product_ids": [99]}
    _patch_common(monkeypatch, user_data, root_post)

    product = {"name": "Produto X", "commission_link": "http://x"}
    monkeypatch.setattr(
        module.products, "get", lambda user_id, product_id, profile_id: product,
    )

    calls = {}

    def fake_post_product(app_id, secret, user_access_token, product_arg, ig_user_id):
        calls["args"] = (
            app_id, secret, user_access_token, product_arg, ig_user_id
        )
        return "media-2"

    monkeypatch.setattr(module.InstagramAPI, "post_product", fake_post_product)
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)

    module.bot_post_instagram("job-2")

    assert calls["args"] == (
        "app-1", "secret-1", "user-token-1", product, "ig-user-1"
    )


def test_bot_post_instagram_with_image_uses_image_publisher(monkeypatch):
    user_data = _user_data()
    image = {"type": "IMAGE", "file_path": "web/media/7/image.jpg"}
    root_post = {"text": "foto", "product_ids": [], "medias": [image]}
    _patch_common(monkeypatch, user_data, root_post)

    calls = {}
    monkeypatch.setattr(
        module,
        "_publish_image",
        lambda app_id, secret, token, ig_user_id, media, caption: calls.update(
            args=(app_id, secret, token, ig_user_id, media, caption)
        ),
    )
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)

    module.bot_post_instagram("job-image")

    assert calls["args"] == (
        "app-1", "secret-1", "user-token-1", "ig-user-1", image, "foto"
    )


def test_bot_post_instagram_failure_records_activity_and_does_not_raise(monkeypatch):
    user_data = _user_data()
    root_post = {"text": "oi", "product_ids": []}
    _patch_common(monkeypatch, user_data, root_post)

    def fake_post_text(*args, **kwargs):
        raise Exception("instagram_content_publish not approved for this app")

    monkeypatch.setattr(module.InstagramAPI, "post_text", fake_post_text)

    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata)
        ),
    )

    module.bot_post_instagram("job-3")

    assert len(activities) == 1
    user_id, activity_type, metadata = activities[0]
    assert activity_type == ActivityType.BOT_POST_FAILURE
    assert "instagram_content_publish" in metadata["metadata"]["error"]
