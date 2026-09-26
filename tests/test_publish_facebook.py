"""Facebook: credencial com page_id persiste e o job de post usa o
page_id salvo (nunca hardcoded) ao chamar a API do Facebook. Mesmo
padrão de tests/test_publish.py (Threads) — chamada real à Graph API
mockada."""
import pytest

from shopee_bot.database import get_conn, put_conn, posts, schedulers, \
    activities, facebook_credentials
from shopee_bot.scheduler.bot_post_facebook import bot_post_facebook
import shopee_bot.apis.facebook as FacebookAPI


@pytest.fixture
def facebook_user(test_user):
    conn = get_conn()
    with conn.transaction():
        facebook_credentials.insert(
            test_user["id"],
            {
                "app_id": "app-123",
                "secret": "secret-123",
                "page_id": "page-456",
                "status": True,
            },
            conn,
        )
    put_conn(conn)
    return test_user


def _create_post_and_job(user_id, text="Post de teste do Facebook"):
    post_id = posts.insert(user_id, {"text": text, "post_id": None})

    conn = get_conn()
    job_id = schedulers.insert(
        user_id,
        {
            "post_id": post_id,
            "func": "bot_post_facebook",
            "trigger": "date",
        },
        conn,
    )
    put_conn(conn)
    return post_id, job_id


def test_facebook_credential_saves_and_returns_page_id(facebook_user):
    saved = facebook_credentials.get_by_user_id(facebook_user["id"])
    assert saved["facebook_app_id"] == "app-123"
    assert saved["facebook_page_id"] == "page-456"
    assert saved["facebook_status"] is True


def test_bot_post_facebook_uses_saved_page_id(facebook_user, monkeypatch):
    _, job_id = _create_post_and_job(facebook_user["id"])

    calls = []

    def _fake_post_text(app_id, secret, page_id, text):
        calls.append((app_id, secret, page_id, text))
        return {"id": "fake_post_id"}

    monkeypatch.setattr(FacebookAPI, "post_text", _fake_post_text)

    bot_post_facebook(job_id)

    assert len(calls) == 1
    app_id, secret, page_id, text = calls[0]
    assert app_id == "app-123"
    assert secret == "secret-123"
    assert page_id == "page-456"
    assert text == "Post de teste do Facebook"

    recent, _ = activities.query_activities_paginated(
        facebook_user["id"], None, 1
    )
    assert recent[0]["name"] == "bot_post_success"


def test_bot_post_facebook_failure_logs_activity_and_does_not_raise(
    facebook_user, monkeypatch
):
    _, job_id = _create_post_and_job(
        facebook_user["id"], text="Post que vai falhar"
    )

    def _boom(*a, **kw):
        raise RuntimeError("falha simulada de rede")

    monkeypatch.setattr(FacebookAPI, "post_text", _boom)

    # não deve levantar exceção pro chamador (scheduler não pode cair)
    bot_post_facebook(job_id)

    recent, _ = activities.query_activities_paginated(
        facebook_user["id"], None, 1
    )
    assert recent[0]["name"] == "bot_post_failure"
