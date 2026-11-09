"""
Testes de scheduler/bot_post_tiktok.py — cobre o caso central da tarefa
(post sem vídeo falha com mensagem clara, sem chamar a API nem estourar
exceção) e o caminho feliz/de falha de API, tudo mockado via
monkeypatch (nada de banco ou rede de verdade — ver tests/scheduler/
conftest.py).
"""

import sys

# import (não "from X import Y") de propósito: scheduler/__init__.py faz
# "from .bot_post_tiktok import bot_post_tiktok", o que sobrescreve o
# atributo `bot_post_tiktok` do pacote com a FUNÇÃO — pegar o submódulo
# teria que ser via sys.modules, não via atributo do pacote (que já não
# é mais o módulo depois desse import).
import shopee_bot.scheduler.bot_post_tiktok  # noqa: F401
from shopee_bot.database.activity_types import ActivityType

module = sys.modules["shopee_bot.scheduler.bot_post_tiktok"]


def _user_data(**overrides):
    base = {
        "username": "fulano",
        "tiktok_app_id": "app-1",
        "tiktok_secret": "secret-1",
        "tiktok_user_access_token": "user-token-1",
        "tiktok_refresh_token": "refresh-1",
        "tiktok_open_id": "open-1",
    }
    base.update(overrides)
    return base


def _patch_common(monkeypatch, user_data, post_data):
    monkeypatch.setattr(
        module.schedulers, "get_by_id",
        lambda job_id: {"user_id": 42, "post_id": 7, "profile_id": "profile-1"},
    )
    monkeypatch.setattr(
        module.tiktok_credentials, "get_by_user_id",
        lambda user_id, profile_id=None: user_data,
    )
    monkeypatch.setattr(
        module.posts, "get", lambda user_id, post_id, profile_id: post_data,
    )


def test_bot_post_tiktok_without_video_fails_clearly_and_does_not_call_api(monkeypatch):
    user_data = _user_data()
    root_post = {"text": "post sem vídeo", "medias": []}
    _patch_common(monkeypatch, user_data, [root_post])

    def _boom(*a, **kw):
        raise AssertionError("post_video não deveria ser chamado sem vídeo")

    monkeypatch.setattr(module.TikTokAPI, "post_video", _boom)

    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata)
        ),
    )

    module.bot_post_tiktok("job-1")  # não deve levantar exceção pro chamador

    assert len(activities) == 1
    user_id, activity_type, metadata = activities[0]
    assert user_id == 42
    assert activity_type == ActivityType.BOT_POST_FAILURE
    assert "vídeo" in metadata["metadata"]["error"]


def test_bot_post_tiktok_without_any_media_field_also_fails_clearly(monkeypatch):
    """Post sem a chave "medias" (não só lista vazia) tem que cair no
    mesmo caminho — _video_media não pode estourar KeyError."""
    user_data = _user_data()
    root_post = {"text": "post sem chave medias"}
    _patch_common(monkeypatch, user_data, [root_post])

    monkeypatch.setattr(
        module.TikTokAPI, "post_video",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("post_video não deveria ser chamado sem vídeo")
        ),
    )

    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata)
        ),
    )

    module.bot_post_tiktok("job-0")

    assert len(activities) == 1
    assert activities[0][1] == ActivityType.BOT_POST_FAILURE


def test_bot_post_tiktok_with_video_calls_post_video_and_logs_success(monkeypatch):
    user_data = _user_data()
    video_media = {"type": "VIDEO", "file_path": "/tmp/video.mp4"}
    root_post = {"text": "confere esse produto", "medias": [video_media]}
    _patch_common(monkeypatch, user_data, [root_post])

    calls = {}

    def fake_post_video(user_access_token, video_path, text, before_publish=None):
        calls["args"] = (user_access_token, video_path, text)
        return "publish-1"

    monkeypatch.setattr(module.TikTokAPI, "post_video", fake_post_video)

    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata)
        ),
    )

    result = module.bot_post_tiktok("job-2")

    assert calls["args"] == (
        "user-token-1", "/tmp/video.mp4", "confere esse produto"
    )
    assert len(activities) == 1
    user_id, activity_type, metadata = activities[0]
    assert user_id == 42
    assert activity_type == ActivityType.BOT_POST_SUCCESS
    assert metadata["metadata"]["publish_id"] == "publish-1"
    assert result.status == "succeeded"
    assert result.external_id == "publish-1"


def test_bot_post_tiktok_api_failure_records_activity_and_does_not_raise(monkeypatch):
    user_data = _user_data()
    video_media = {"type": "VIDEO", "file_path": "/tmp/video.mp4"}
    root_post = {"text": "oi", "medias": [video_media]}
    _patch_common(monkeypatch, user_data, [root_post])

    def _boom(*a, **kw):
        raise RuntimeError("falha simulada de rede")

    monkeypatch.setattr(module.TikTokAPI, "post_video", _boom)

    activities = []
    monkeypatch.setattr(
        module, "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata)
        ),
    )

    module.bot_post_tiktok("job-3")  # não deve levantar exceção pro chamador

    assert len(activities) == 1
    _, activity_type, metadata = activities[0]
    assert activity_type == ActivityType.BOT_POST_FAILURE
    assert "falha simulada de rede" in metadata["metadata"]["error"]


# --- refresh de token expirado (access_token ~24h) ---------------------

def _setup_refresh(monkeypatch, post_video, refresh):
    video = {"type": "VIDEO", "file_path": "/tmp/v.mp4"}
    _patch_common(monkeypatch, _user_data(), [{"text": "t", "medias": [video]}])
    monkeypatch.setattr(module.TikTokAPI, "post_video", post_video)
    monkeypatch.setattr(module.TikTokAPI, "refresh_user_token", refresh)
    saved, marked, acts = [], [], []
    monkeypatch.setattr(
        module.tiktok_credentials, "update_tokens",
        lambda uid, pid, tokens: saved.append((uid, pid, tokens)),
    )
    monkeypatch.setattr(
        module.tiktok_credentials, "mark_needs_reconnect",
        lambda uid, pid, msg: marked.append((uid, pid, msg)),
    )
    monkeypatch.setattr(
        module, "insert_activities",
        lambda uid, typ, meta, profile_id=None: acts.append((typ, meta)),
    )
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    return saved, marked, acts


def _expired():
    return module.TikTokAPI.TikTokAPIError(
        'Failed to Init Video Post:\nStatus: 401\nText: {"error":{"code":"access_token_invalid"}}'
    )


def test_expired_token_refreshes_saves_and_retries_once(monkeypatch):
    tokens_used = []

    def post_video(token, path, text, before_publish=None):
        tokens_used.append(token)
        if token == "user-token-1":
            raise _expired()
        return "pub-1"

    saved, marked, acts = _setup_refresh(
        monkeypatch, post_video,
        lambda ck, cs, rt: {"access_token": "new-at", "refresh_token": "new-rt"},
    )
    module.bot_post_tiktok("j")

    assert tokens_used == ["user-token-1", "new-at"]
    assert saved == [(42, "profile-1", {"access_token": "new-at", "refresh_token": "new-rt"})]
    assert not marked
    assert acts[0][0] == ActivityType.BOT_POST_SUCCESS


def test_refresh_failure_marks_reconnect_and_fails_without_secrets(monkeypatch):
    def refresh(ck, cs, rt):
        raise module.TikTokAPI.TikTokAPIError("boom refresh-1 secret-1")

    def post_video(token, path, text):
        raise _expired()

    saved, marked, acts = _setup_refresh(monkeypatch, post_video, refresh)
    module.bot_post_tiktok("j")

    assert not saved
    assert marked == [(42, "profile-1", module.RECONNECT_MESSAGE)]
    typ, meta = acts[0]
    assert typ == ActivityType.BOT_POST_FAILURE
    error = meta["metadata"]["error"]
    assert error == module.RECONNECT_MESSAGE
    assert "refresh-1" not in error and "secret-1" not in error


def test_new_tokens_saved_even_if_retry_fails(monkeypatch):
    def post_video(token, path, text):
        raise _expired() if token == "user-token-1" else RuntimeError("falha 2")

    saved, marked, acts = _setup_refresh(
        monkeypatch, post_video,
        lambda ck, cs, rt: {"access_token": "new-at", "refresh_token": "new-rt"},
    )
    module.bot_post_tiktok("j")

    assert saved and saved[0][2]["refresh_token"] == "new-rt"
    assert acts[0][0] == ActivityType.BOT_POST_FAILURE


def test_non_auth_error_does_not_refresh(monkeypatch):
    def refresh(*a):
        raise AssertionError("não deveria renovar")

    def post_video(token, path, text):
        raise RuntimeError("rede caiu")

    _setup_refresh(monkeypatch, post_video, refresh)
    module.bot_post_tiktok("j")


def test_refresh_is_scoped_by_profile(monkeypatch):
    video = {"type": "VIDEO", "file_path": "/tmp/v.mp4"}
    _patch_common(monkeypatch, _user_data(), [{"text": "t", "medias": [video]}])
    monkeypatch.setattr(
        module.schedulers, "get_by_id",
        lambda j: {"user_id": 42, "post_id": 7, "profile_id": "prof-9"},
    )
    monkeypatch.setattr(
        module.TikTokAPI, "post_video",
        lambda t, p, x: "ok" if t == "n" else (_ for _ in ()).throw(_expired()),
    )
    monkeypatch.setattr(
        module.TikTokAPI, "refresh_user_token",
        lambda *a: {"access_token": "n"},
    )
    saved = []
    monkeypatch.setattr(
        module.tiktok_credentials, "update_tokens",
        lambda uid, pid, t: saved.append((uid, pid)),
    )
    monkeypatch.setattr(module, "insert_activities", lambda *a, **k: None)
    module.bot_post_tiktok("j")
    assert saved == [(42, "prof-9")]
