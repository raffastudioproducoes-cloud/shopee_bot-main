import sys

import shopee_bot.scheduler as scheduler


def test_053_publish_jobs_migration_defines_idempotency_and_terminal_states():
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "053_create_publish_jobs.sql"
    ).read_text(encoding="utf-8").lower()

    assert "idempotency_key text not null unique" in sql
    assert "status text not null default 'pending'" in sql
    assert "'unknown'" in sql
    assert "claim_token uuid" in sql


def test_enqueue_reuses_the_same_idempotency_key(monkeypatch):
    from shopee_bot.database import publish_jobs

    seen = {}

    def fake_query(sql, args, one=False):
        seen.update(sql=sql, args=args, one=one)
        return {"id": "queue-1", "status": "pending"}

    monkeypatch.setattr(publish_jobs, "query_db", fake_query)

    item = publish_jobs.enqueue(
        scheduler_id="schedule-1",
        post_id=7,
        user_id="user-1",
        profile_id="profile-1",
        network="threads",
        idempotency_key="schedule-1:2026-10-16T10:30",
    )

    assert item == {"id": "queue-1", "status": "pending"}
    assert seen["args"][-1] == "schedule-1:2026-10-16T10:30"
    assert "on conflict (idempotency_key)" in seen["sql"].lower()


def test_claim_returns_only_the_worker_that_won_the_atomic_update(monkeypatch):
    from shopee_bot.database import publish_jobs

    responses = iter([
        {"id": "queue-1", "claim_token": "claim-1"},
        None,
        None,
        None,
        None,
    ])
    monkeypatch.setattr(publish_jobs, "query_db", lambda *_args, **_kwargs: next(responses))

    winners = [publish_jobs.claim("queue-1", f"worker-{n}", 300) for n in range(5)]

    assert winners == [{"id": "queue-1", "claim_token": "claim-1"}, None, None, None, None]


def test_claim_query_never_retries_a_running_item(monkeypatch):
    from shopee_bot.database import publish_jobs

    seen = {}

    def fake_query(sql, args, one=False):
        seen.update(sql=sql, args=args, one=one)
        return None

    monkeypatch.setattr(publish_jobs, "query_db", fake_query)

    assert publish_jobs.claim("queue-1", "worker-1", 300) is None
    assert "status = 'pending'" in seen["sql"].lower()
    assert "status = 'running'" not in seen["sql"].lower().split("for update skip locked")[0]


def test_expired_running_item_after_external_call_becomes_unknown(monkeypatch):
    from shopee_bot.database import publish_jobs

    seen = {}
    monkeypatch.setattr(publish_jobs, "query_db", lambda sql, args: seen.update(sql=sql, args=args) or [])

    assert publish_jobs.expire_running(300) == []
    assert "preflight_claim_token is distinct from claim_token" in seen["sql"].lower()
    assert "status = 'running'" in seen["sql"].lower()
    assert seen["args"] == (5, 5, 5, 300)


def test_execute_publication_does_not_repeat_unknown_delivery(monkeypatch):
    queue = sys.modules.get("shopee_bot.database.publish_jobs")
    assert queue is not None

    calls = []
    monkeypatch.setattr(
        scheduler.schedulers,
        "get_by_id",
        lambda _job_id: {
            "id": "schedule-1", "post_id": 7, "user_id": "user-1",
            "profile_id": "profile-1", "func": "bot_post", "trigger": "date",
        },
    )
    monkeypatch.setattr(scheduler.publication_claims, "try_claim", lambda *_: "lease-1")
    monkeypatch.setattr(scheduler.publication_claims, "release", lambda *_: None)
    monkeypatch.setattr(queue, "enqueue", lambda **_kwargs: {"id": "queue-1", "status": "unknown"})
    monkeypatch.setattr(queue, "claim", lambda *_: calls.append("claim"))
    monkeypatch.setattr(scheduler, "bot_post", lambda *_: calls.append("publish"))

    scheduler.execute_publication("schedule-1")

    assert calls == []


def test_drain_publish_jobs_retries_only_recoverable_queue_items(monkeypatch):
    queue = sys.modules["shopee_bot.database.publish_jobs"]
    calls = []
    monkeypatch.setattr(
        queue,
        "recoverable",
        lambda _lease: [{"id": "queue-1", "scheduler_id": "schedule-1"}],
    )
    monkeypatch.setattr(queue, "expire_running", lambda lease: calls.append(("expired", lease)) or [])
    monkeypatch.setattr(
        scheduler.schedulers,
        "get_by_id",
        lambda _job_id: {"func": "bot_post"},
    )
    monkeypatch.setattr(
        scheduler,
        "_execute_publish_item",
        lambda item_id, job_data: calls.append((item_id, job_data["func"])),
    )

    scheduler.drain_publish_jobs()

    assert calls == [("expired", scheduler.PUBLISH_JOB_LEASE_SECONDS), ("queue-1", "bot_post")]


def test_finish_redacts_token_from_provider_error(monkeypatch):
    from shopee_bot.database import publish_jobs

    seen = {}
    monkeypatch.setattr(publish_jobs, "query_db", lambda sql, args, one=False: seen.update(args=args) or {"id": "queue-1"})

    publish_jobs.finish("queue-1", "claim-1", "unknown", error="access_token=private-value")
    assert "private-value" not in seen["args"][2]



def test_concurrent_posts_keep_distinct_occurrence_keys(monkeypatch):
    """Mesmo segundo/produto não deve deduplicar posts diferentes ou clientes."""
    jobs = {
        "schedule-a": {"id": "schedule-a", "post_id": 100, "user_id": "user-a", "profile_id": "profile-a", "func": "bot_post", "trigger": "cron"},
        "schedule-b": {"id": "schedule-b", "post_id": 101, "user_id": "user-a", "profile_id": "profile-a", "func": "bot_post", "trigger": "cron"},
        "schedule-c": {"id": "schedule-c", "post_id": 102, "user_id": "user-b", "profile_id": "profile-b", "func": "bot_post", "trigger": "cron"},
        "schedule-d": {"id": "schedule-d", "post_id": 103, "user_id": "user-a", "profile_id": "profile-other", "func": "bot_post", "trigger": "cron"},
    }
    enqueued = []
    executed = []
    released = []
    monkeypatch.setattr(scheduler.schedulers, "get_by_id", lambda job_id: jobs[job_id])
    monkeypatch.setattr(scheduler.publication_claims, "try_claim", lambda key, lease: f"lease-{key}")
    monkeypatch.setattr(scheduler.publication_claims, "release", lambda *args: released.append(args))
    monkeypatch.setattr(scheduler.publish_jobs, "enqueue",
                        lambda **kwargs: enqueued.append(kwargs) or {"id": f"queue-{kwargs['scheduler_id']}", "status": "pending"})
    monkeypatch.setattr(scheduler, "_execute_publish_item",
                        lambda queue_id, job_data: executed.append((queue_id, job_data["post_id"])))
    monkeypatch.setattr(scheduler, "_shutting_down", False)

    for identifier in jobs:
        scheduler.execute_publication(identifier)

    assert len(executed) == 4
    assert {data["post_id"] for data in enqueued} == {100, 101, 102, 103}
    assert len({data["idempotency_key"] for data in enqueued}) == 4
    assert len({data["scheduler_id"] for data in enqueued}) == 4
    assert [(x["user_id"], x["profile_id"]) for x in enqueued] == [
        ("user-a", "profile-a"), ("user-a", "profile-a"),
        ("user-b", "profile-b"), ("user-a", "profile-other"),
    ]
    assert len(released) == 4


def test_enqueue_rejects_cross_tenant_conflict_even_for_same_key(monkeypatch):
    from shopee_bot.database import publish_jobs

    queries = []
    monkeypatch.setattr(publish_jobs, "query_db",
                        lambda sql, args, one=False: queries.append(sql) or None)

    import pytest
    with pytest.raises(RuntimeError, match="Conflito de identidade"):
        publish_jobs.enqueue(
            scheduler_id="schedule-a", post_id=17, user_id="user-a",
            profile_id="profile-a", network="threads", idempotency_key="same-key",
        )
    sql = queries[0].lower()
    assert "publish_jobs.scheduler_id = excluded.scheduler_id" in sql
    assert "publish_jobs.user_id = excluded.user_id" in sql
    assert "publish_jobs.profile_id is not distinct from excluded.profile_id" in sql
    assert "publish_jobs.post_id = excluded.post_id" in sql


def test_claim_rejects_mismatched_owner_and_profile(monkeypatch):
    from shopee_bot.database import publish_jobs

    seen = {}
    monkeypatch.setattr(publish_jobs, "query_db",
                        lambda sql, args, one=False: seen.update(sql=sql) or None)

    assert publish_jobs.claim("queue-a", "worker", 600) is None
    sql = seen["sql"].lower()
    assert "schedule.user_id = job.user_id" in sql
    assert "schedule.profile_id is not distinct from job.profile_id" in sql
    assert "post.user_id = job.user_id" in sql
    assert "for update of job skip locked" in sql
