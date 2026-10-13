"""Regressões do publicador X usando o OAuth global da plataforma."""

import sys
from datetime import datetime, timedelta, timezone

import shopee_bot.scheduler.bot_post_x  # noqa: F401
from shopee_bot.database.activity_types import ActivityType


module = sys.modules["shopee_bot.scheduler.bot_post_x"]


def test_expired_x_token_refreshes_with_global_oauth_and_scopes_saved_tokens(monkeypatch):
    """A luz e o scheduler devem usar o mesmo X_CLIENT_ID/X_CLIENT_SECRET."""
    profile_id = "profile-7"
    refreshed = []
    published = []
    activities = []

    monkeypatch.setattr(
        module.schedulers,
        "get_by_id",
        lambda job_id: {"user_id": 42, "post_id": 9, "profile_id": profile_id},
    )
    monkeypatch.setattr(
        module.x_credentials,
        "get_by_user_id",
        lambda user_id, profile_id=None: {
            "username": "cliente",
            "x_access_token": "expired-access-token",
            "x_refresh_token": "refresh-token",
            "token_expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
            # Valores legados propositalmente diferentes do app OAuth global.
            "x_app_id": "legacy-client-id",
            "x_secret": "legacy-client-secret",
        },
    )
    monkeypatch.setattr(
        module.posts, "get", lambda user_id, post_id, saved_profile_id: [{"text": "teste"}]
    )
    async def refresh_access_token(token):
        assert token == "refresh-token"
        return {"access_token": "fresh-access-token", "refresh_token": "fresh-refresh-token"}

    monkeypatch.setattr(module.x_oauth, "refresh_access_token", refresh_access_token)
    monkeypatch.setattr(
        module.x_credentials,
        "update_tokens",
        lambda user_id, saved_profile_id, tokens: refreshed.append((user_id, saved_profile_id, tokens)),
    )
    monkeypatch.setattr(
        module.XAPI,
        "post_text",
        lambda access_token, text, reply_to_id=None: published.append((access_token, text)) or {"id": "x-1"},
    )
    monkeypatch.setattr(
        module,
        "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata, profile_id)
        ),
    )

    module.bot_post_x("job-1")

    assert refreshed == [
        (42, profile_id, {"access_token": "fresh-access-token", "refresh_token": "fresh-refresh-token"})
    ]
    assert published == [("fresh-access-token", "teste")]
    assert activities[0][1] == ActivityType.BOT_POST_SUCCESS


def test_disabled_x_job_logs_and_skips_before_api_calls(monkeypatch, caplog):
    from shopee_bot.api import network_limits

    monkeypatch.setitem(
        network_limits.DISABLED_NETWORKS,
        "x",
        "X estará disponível em um plano pago em breve",
    )
    monkeypatch.setattr(
        module.schedulers,
        "get_by_id",
        lambda job_id: {"user_id": 42, "post_id": 9, "profile_id": "profile-7"},
    )
    monkeypatch.setattr(
        module.x_credentials,
        "get_by_user_id",
        lambda *_args: (_ for _ in ()).throw(AssertionError("nao deve ler credencial X")),
    )
    monkeypatch.setattr(
        module.XAPI,
        "post_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deve chamar API X")),
    )

    module.bot_post_x("job-1")

    assert "X estará disponível em um plano pago em breve" in caplog.text


# --- single_image: upload via POST /2/media/upload (escopo media.write) ---

import pytest  # noqa: E402

from shopee_bot.apis import x as xapi  # noqa: E402
from shopee_bot.scheduler import media_delivery  # noqa: E402
from tests.scheduler.meta_fakes import FakeGraph, FakeResponse, FakeStorage  # noqa: E402

UPLOAD = ("POST", xapi.MEDIA_UPLOAD_URL)
TWEET = ("POST", f"{xapi.API_BASE}/tweets")


FULL_SCOPE = "tweet.read tweet.write users.read media.write offline.access"


def _setup_image(monkeypatch, graph, medias, scope=FULL_SCOPE):
    monkeypatch.setattr(xapi.requests, "post", graph.post)
    monkeypatch.setattr(xapi.requests, "get", graph.get)
    monkeypatch.setattr(module.requests, "get", graph.get)
    monkeypatch.setattr(media_delivery, "_storage", lambda: FakeStorage())
    monkeypatch.setattr(module.schedulers, "get_by_id",
                        lambda j: {"user_id": 1, "post_id": 2, "profile_id": "p"})
    monkeypatch.setattr(module.x_credentials, "get_by_user_id",
                        lambda u, p: {"username": "u", "x_access_token": "tok", "x_scope": scope})
    monkeypatch.setattr(module.posts, "get", lambda u, post, p: [{"text": "oi", "medias": medias}])
    acts = []
    monkeypatch.setattr(module, "insert_activities",
                        lambda u, t, m, profile_id=None: acts.append((t, m)))
    return acts


def _img(name="a.jpg"):
    return {"type": "IMAGE", "file_path": f"storage://bucket/{name}", "file_name": name}


def _signed_get(name="a.jpg"):
    return ("GET", f"https://signed.example/bucket/{name}?token=t")


def test_imagem_unica_sobe_media_e_publica_com_media_ids(monkeypatch):
    graph = FakeGraph({
        _signed_get(): [FakeResponse(content=b"IMG")],
        UPLOAD: [{"data": {"id": "m1"}}],
        TWEET: [{"data": {"id": "t1"}}],
    })
    acts = _setup_image(monkeypatch, graph, [_img()])
    module.bot_post_x("j")
    up = next(c for c in graph.calls if c["url"] == xapi.MEDIA_UPLOAD_URL)
    assert up["headers"]["Authorization"] == "Bearer tok"
    assert up["data"] == {"media_category": "tweet_image"}
    assert up["files"]["media"][1] == b"IMG"
    tweet = next(c for c in graph.calls if c["url"].endswith("/tweets"))
    assert tweet["json"]["media"] == {"media_ids": ["m1"]}
    assert acts[-1][0] == ActivityType.BOT_POST_SUCCESS


@pytest.mark.parametrize("status", [401, 403])
def test_conexao_sem_media_write_falha_pedindo_reconexao_sem_publicar_texto(monkeypatch, status):
    graph = FakeGraph({
        _signed_get(): [FakeResponse(content=b"IMG")],
        UPLOAD: [FakeResponse({"title": "Forbidden"}, status_code=status)],
    })
    acts = _setup_image(monkeypatch, graph, [_img()])
    module.bot_post_x("j")
    assert TWEET[1] not in graph.urls("POST")
    assert acts[-1][0] == ActivityType.BOT_POST_FAILURE
    err = acts[-1][1]
    assert "reconecte" in str(err).lower() and "media.write" in str(err)


def test_midia_nao_suportada_no_x_falha_sem_cair_para_texto(monkeypatch):
    graph = FakeGraph({})
    acts = _setup_image(monkeypatch, graph, [_img("a.jpg"), _img("b.jpg")])
    module.bot_post_x("j")
    assert graph.calls == []
    assert acts[-1][0] == ActivityType.BOT_POST_FAILURE


def test_escopo_oauth_inclui_media_write():
    from shopee_bot.api import x_oauth
    assert "media.write" in x_oauth.DEFAULT_SCOPES.split()
    assert "media.write" in xapi.DEFAULT_SCOPES.split()


@pytest.mark.parametrize("scope", [None, "", "tweet.read tweet.write users.read offline.access"])
def test_sem_media_write_bloqueia_antes_do_primeiro_upload(monkeypatch, scope):
    graph = FakeGraph({})
    acts = _setup_image(monkeypatch, graph, [_img()], scope=scope)
    module.bot_post_x("j")
    assert graph.calls == []  # nem download, nem upload, nem tweet
    assert acts[-1][0] == ActivityType.BOT_POST_FAILURE
    assert "reconecte o X" in str(acts[-1][1])


def test_post_so_texto_nao_exige_media_write(monkeypatch):
    graph = FakeGraph({TWEET: [{"data": {"id": "t1"}}]})
    acts = _setup_image(monkeypatch, graph, [], scope=None)
    module.bot_post_x("j")
    assert acts[-1][0] == ActivityType.BOT_POST_SUCCESS


def test_refresh_atualiza_escopo_em_memoria(monkeypatch):
    from datetime import datetime, timedelta, timezone

    async def refresh(token):
        return {"access_token": "new", "refresh_token": "r2", "scope": FULL_SCOPE}

    monkeypatch.setattr(module.x_oauth, "refresh_access_token", refresh)
    monkeypatch.setattr(module.x_credentials, "update_tokens", lambda *a: None)
    data = {
        "x_refresh_token": "r", "x_access_token": "old", "x_scope": None,
        "token_expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    assert module._ensure_fresh_token(1, "p", data)["x_scope"] == FULL_SCOPE
