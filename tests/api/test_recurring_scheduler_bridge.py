"""Contrato de agendamento entre FastAPI e Flask, sem publicação externa."""

import asyncio
from types import SimpleNamespace

import pytest

from api import internal_client
from api.routers import posts


def test_internal_bridge_rejects_missing_or_invalid_job_id(monkeypatch):
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(
                status_code=201,
                json=lambda: {"job_id": "None"},
            )

    monkeypatch.setattr(internal_client.httpx, "AsyncClient", lambda **_kw: FakeClient())

    with pytest.raises(internal_client.InternalApiError, match="ID inválido"):
        asyncio.run(internal_client.create_scheduler_job(
            user_id="user-1", post_id=7, func="bot_post",
            trigger="cron", time="13:00", days_of_week=[0],
            profile_id="profile-a",
        ))


def test_internal_bridge_returns_real_uuid(monkeypatch):
    uuid = "8cbe9ecb-3dc7-4fe5-a864-573c385c73c4"

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(status_code=201, json=lambda: {"job_id": uuid})

    monkeypatch.setattr(internal_client.httpx, "AsyncClient", lambda **_kw: FakeClient())
    result = asyncio.run(internal_client.create_scheduler_job(
        user_id="user-1", post_id=7, func="bot_post",
        trigger="cron", time="13:00", days_of_week=[0],
        profile_id="profile-a",
    ))
    assert result == uuid


def _schedule():
    return posts.PostSchedule(
        trigger="cron", time="13:00",
        times=["13:00", "15:00", "18:00"],
        days_of_week=[0], day_of_week=0,
    )


def test_three_recurring_times_are_registered_under_active_profile(monkeypatch):
    created = []
    ids = [
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
        "33333333-3333-4333-8333-333333333333",
    ]

    async def create(**kwargs):
        created.append(kwargs)
        return ids[len(created) - 1]

    async def remove(*_args):
        pytest.fail("Não deveria desfazer agendamentos válidos")

    monkeypatch.setattr(posts, "create_scheduler_job", create)
    monkeypatch.setattr(posts, "remove_scheduler_job", remove)

    asyncio.run(posts._create_schedule_jobs(
        42, 7, "bot_post", _schedule(), "profile-a",
    ))
    assert [job["time"] for job in created] == ["13:00", "15:00", "18:00"]
    assert all(job["profile_id"] == "profile-a" for job in created)
    assert all(job["days_of_week"] == [0] for job in created)


def test_recurring_failure_undoes_previous_time_using_real_id(monkeypatch):
    created = []
    removed = []
    first_id = "11111111-1111-4111-8111-111111111111"

    async def create(**kwargs):
        created.append(kwargs["time"])
        if len(created) == 2:
            raise internal_client.InternalApiError("create_scheduler_job falhou: HTTP 503")
        return first_id

    async def remove(user_id, job_id):
        removed.append((user_id, job_id))

    monkeypatch.setattr(posts, "create_scheduler_job", create)
    monkeypatch.setattr(posts, "remove_scheduler_job", remove)
    with pytest.raises(internal_client.InternalApiError):
        asyncio.run(posts._create_schedule_jobs(
            42, 7, "bot_post", _schedule(), "profile-a",
        ))

    assert created == ["13:00", "15:00"]
    assert removed == [(42, first_id)]


def test_scheduler_status_bridge_reads_boolean_without_creating_job(monkeypatch):
    calls = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **_kwargs):
            calls.append(url)
            return SimpleNamespace(status_code=200, json=lambda: {"available": False})

    monkeypatch.setattr(internal_client.httpx, "AsyncClient", lambda **_kw: FakeClient())
    assert asyncio.run(internal_client.scheduler_availability()) is False
    assert len(calls) == 1
    assert calls[0].endswith("/internal/scheduler/status")


def test_scheduler_status_bridge_fails_closed_on_invalid_response(monkeypatch):
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {"available": "false"})

    monkeypatch.setattr(internal_client.httpx, "AsyncClient", lambda **_kw: FakeClient())
    with pytest.raises(internal_client.InternalApiError, match="Resposta inválida"):
        asyncio.run(internal_client.scheduler_availability())


def test_batch_blocks_without_writing_when_scheduler_is_disabled(monkeypatch):
    from fastapi import HTTPException

    async def scheduler_off():
        return False

    def no_mutation(*_args, **_kwargs):
        pytest.fail("Mídias e posts não devem ser escritos com agendador desativado")

    monkeypatch.setattr(posts, "scheduler_availability", scheduler_off)
    monkeypatch.setattr(posts, "_validate_product_ids", lambda *_args: None)
    monkeypatch.setattr(posts, "_get_owned_ready_drafts", no_mutation)
    monkeypatch.setattr(posts, "_create_thread", no_mutation)

    body = posts.PostBatchCreate(
        compositions=[posts.PostComposition(network="threads", texts=["Teste não publicável"])],
        schedule=_schedule(),
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(posts.create_posts_batch(body, user_id=42, profile_id="profile-a"))
    assert exc.value.status_code == 503
    assert "agendador" in exc.value.detail.lower()
    assert "rascunho" in exc.value.detail.lower()


def test_scheduler_status_endpoint_reports_disabled_without_posting(monkeypatch):
    async def scheduler_off():
        return False

    monkeypatch.setattr(posts, "scheduler_availability", scheduler_off)
    result = asyncio.run(posts.get_scheduler_status(_user_id=42))
    assert result["available"] is False
    assert "nenhuma publicação" in result["message"].lower()
