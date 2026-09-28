"""Fluxo crítico: criar post e publicar (Sprint 1 — retry/log de falha).

Publicação testada na camada de negócio, com a chamada real ao
Threads mockada — não bate na API de verdade (isso é o item 1.6 do
roadmap, testado à parte com credencial real). Aqui a garantia é: o
job publica, loga sucesso; se falhar, loga falha e não quebra.
"""
from shopee_bot.database import get_conn, put_conn, posts, schedulers, \
    activities
from shopee_bot.scheduler.bot_post import bot_post
import shopee_bot.apis.threads as ThreadsAPI


def _create_post_and_job(user_id, text="Post de teste automatizado"):
    post_id = posts.insert(user_id, {"text": text, "post_id": None})

    conn = get_conn()
    job_id = schedulers.insert(
        user_id,
        {
            "post_id": post_id,
            "func": "bot_post",
            "trigger": "date",
        },
        conn
    )
    put_conn(conn)
    return post_id, job_id


def test_create_post(test_user):
    post_id, _ = _create_post_and_job(test_user["id"])
    saved = posts.get(test_user["id"], post_id)
    assert saved[0]["text"] == "Post de teste automatizado"


def test_publish_success_logs_activity(test_user, monkeypatch):
    _, job_id = _create_post_and_job(test_user["id"])

    monkeypatch.setattr(
        ThreadsAPI, "make_post", lambda *a, **kw: "fake_thread_item_id"
    )

    bot_post(job_id)

    recent, _ = activities.query_activities_paginated(test_user["id"], None, 1)
    assert recent[0]["name"] == "bot_post_success"


def test_publish_failure_logs_activity_and_does_not_raise(test_user, monkeypatch):
    _, job_id = _create_post_and_job(
        test_user["id"], text="Post que vai falhar"
    )

    def _boom(*a, **kw):
        raise RuntimeError("falha simulada de rede")

    monkeypatch.setattr(ThreadsAPI, "make_post", _boom)

    # não deve levantar exceção pro chamador (scheduler não pode cair)
    bot_post(job_id)

    recent, _ = activities.query_activities_paginated(test_user["id"], None, 1)
    assert recent[0]["name"] == "bot_post_failure"
