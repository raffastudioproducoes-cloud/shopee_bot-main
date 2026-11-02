"""Regressão: criar post sem especificar rede (ou explicitamente com
'threads') tem que continuar gerando func="bot_post" no scheduler,
exatamente como antes do campo `network` existir.

Cobre os dois lugares que resolvem func a partir da rede:
- api/routers/posts.py (schema Pydantic usado pelo frontend React)
- shopee_bot/database/schedulers.py (mapa usado pelo painel Flask
  legado, removido; o mapa segue como fallback)
- shopee_bot/database/posts.py (fallback de default na hora do INSERT)

Não exercita o endpoint FastAPI inteiro (bateria em Supabase real, fora
de escopo aqui) — testa a resolução de func isoladamente, que é
exatamente a lógica nova introduzida por essa mudança.
"""

import pytest
import asyncio
from pydantic import ValidationError

from api.routers.posts import (
    PostBatchCreate,
    PostCreate,
    PostSchedule,
    NETWORK_FUNC_MAP as API_NETWORK_FUNC_MAP,
)
from api.routers import posts as posts_router
from shopee_bot.database.schedulers import NETWORK_FUNC_MAP as DB_NETWORK_FUNC_MAP
import shopee_bot.database.posts as posts_db


def _schedule() -> PostSchedule:
    return PostSchedule(trigger="cron", time="09:00", days_of_week=[0])


class TestApiNetworkDefaultsToThreads:
    def test_publish_immediately_requires_one_off_schedule(self):
        with pytest.raises(ValidationError):
            PostBatchCreate(
                compositions=[{"network": "threads", "texts": ["oi"]}],
                schedule={"trigger": "cron", "time": "09:00", "days_of_week": [0]},
                publish_immediately=True,
            )

    def test_publish_immediately_is_explicit_in_batch(self):
        body = PostBatchCreate(
            compositions=[{"network": "threads", "texts": ["oi"]}],
            schedule={"trigger": "date", "run_date": "2030-01-01T00:00:00Z"},
            publish_immediately=True,
        )
        assert body.publish_immediately is True

    def test_now_job_never_appears_as_scheduled(self):
        job = {"id": "safety-job", "trigger": "date"}
        assert posts_router._is_scheduled(job, {"publish_immediately": True}) is False
        assert posts_router._is_scheduled(job, {"publish_immediately": False}) is True

    def test_recurring_schedule_accepts_five_unique_times(self):
        times = ["09:00", "10:15", "12:30", "15:45", "18:00"]
        schedule = PostSchedule(trigger="cron", times=times, days_of_week=[0, 2])
        assert schedule.times == times
        assert schedule.time == times[0]

    @pytest.mark.parametrize("times", [[], ["09:00"] * 2, ["25:00"], ["09:99"], ["09:00"] * 6])
    def test_recurring_schedule_rejects_invalid_times(self, times):
        with pytest.raises(ValidationError):
            PostSchedule(trigger="cron", times=times, days_of_week=[0])

    def test_recurring_schedule_creates_each_time_and_rolls_back_on_error(self, monkeypatch):
        created, removed = [], []

        async def create_scheduler_job(**fields):
            if fields["time"] == "12:00":
                raise posts_router.InternalApiError("failed")
            created.append(fields["time"])
            return fields["time"]

        async def remove_scheduler_job(user_id, job_id):
            removed.append(job_id)

        monkeypatch.setattr(posts_router, "create_scheduler_job", create_scheduler_job)
        monkeypatch.setattr(posts_router, "remove_scheduler_job", remove_scheduler_job)
        schedule = PostSchedule(trigger="cron", times=["09:00", "12:00"], days_of_week=[0])
        with pytest.raises(posts_router.InternalApiError):
            asyncio.run(posts_router._create_schedule_jobs(1, 2, "bot_post", schedule, "profile"))
        assert created == ["09:00"]
        assert removed == ["09:00"]

    def test_recurring_schedule_accepts_one_or_more_weekdays(self):
        schedule = PostSchedule(trigger="cron", time="09:00", days_of_week=[1, 3, 5])

        assert schedule.days_of_week == [1, 3, 5]
        # Compatibilidade com o job antigo e com a coluna legada.
        assert schedule.day_of_week == 1

    @pytest.mark.parametrize("days", [[], [7], [-1], [1, 1], [0, 1, 2, 3, 4, 5, 6, 0]])
    def test_recurring_schedule_rejects_invalid_weekday_sets(self, days):
        with pytest.raises(ValidationError):
            PostSchedule(trigger="cron", time="09:00", days_of_week=days)

    def test_one_off_date_is_rejected_in_creates(self):
        with pytest.raises(ValidationError):
            PostCreate(texts=["oi"], schedule={"trigger": "date", "run_date": "2030-01-01T00:00:00Z"})
        with pytest.raises(ValidationError):
            PostBatchCreate(compositions=[{"network": "threads", "texts": ["oi"]}], schedule={"trigger": "date", "run_date": "2030-01-01T00:00:00Z"})

    def test_network_omitted_defaults_to_threads(self):
        body = PostCreate(texts=["oi"], schedule=_schedule())
        assert body.network == "threads"

    def test_network_omitted_resolves_to_bot_post(self):
        body = PostCreate(texts=["oi"], schedule=_schedule())
        assert API_NETWORK_FUNC_MAP[body.network] == "bot_post"

    def test_network_explicit_threads_resolves_to_bot_post(self):
        body = PostCreate(texts=["oi"], schedule=_schedule(), network="threads")
        assert API_NETWORK_FUNC_MAP[body.network] == "bot_post"

    def test_unknown_network_is_rejected(self):
        with pytest.raises(ValidationError):
            PostCreate(texts=["oi"], schedule=_schedule(), network="myspace")


class TestNetworkFuncMapConsistency:
    def test_threads_maps_to_bot_post(self):
        assert DB_NETWORK_FUNC_MAP["threads"] == "bot_post"

    def test_kwai_is_intentionally_absent(self):
        # sem API pública confirmada ainda — ver docstring do mapa
        assert "kwai" not in API_NETWORK_FUNC_MAP
        assert "kwai" not in DB_NETWORK_FUNC_MAP

    def test_api_and_flask_maps_agree(self):
        assert API_NETWORK_FUNC_MAP == DB_NETWORK_FUNC_MAP


class TestPostsInsertDefaultsNetworkToThreads:
    """shopee_bot/database/posts.py (painel Flask legado)."""

    def test_insert_without_network_key_defaults_to_threads(self, monkeypatch):
        captured = {}

        def fake_execute_db(query, args, open_conn=None):
            captured["args"] = args
            return 123

        monkeypatch.setattr(posts_db, "execute_db", fake_execute_db)

        posts_db.insert("user-id", {"text": "sem rede", "post_id": None})

        # args = (user_id, post_id, text, network) — ver posts_db.insert()
        assert captured["args"][-1] == "threads"

    def test_insert_with_explicit_network_keeps_it(self, monkeypatch):
        captured = {}

        def fake_execute_db(query, args, open_conn=None):
            captured["args"] = args
            return 123

        monkeypatch.setattr(posts_db, "execute_db", fake_execute_db)

        posts_db.insert(
            "user-id", {"text": "com rede", "post_id": None, "network": "x"}
        )

        assert captured["args"][-1] == "x"
