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
from pydantic import ValidationError

from api.routers.posts import (
    PostCreate,
    PostSchedule,
    NETWORK_FUNC_MAP as API_NETWORK_FUNC_MAP,
)
from shopee_bot.database.schedulers import NETWORK_FUNC_MAP as DB_NETWORK_FUNC_MAP
import shopee_bot.database.posts as posts_db


def _schedule() -> PostSchedule:
    return PostSchedule(trigger="date", run_date="2030-01-01T00:00:00")


class TestApiNetworkDefaultsToThreads:
    def test_recurring_schedule_accepts_one_or_more_weekdays(self):
        schedule = PostSchedule(trigger="cron", time="09:00", days_of_week=[1, 3, 5])

        assert schedule.days_of_week == [1, 3, 5]
        # Compatibilidade com o job antigo e com a coluna legada.
        assert schedule.day_of_week == 1

    @pytest.mark.parametrize("days", [[], [7], [-1], [1, 1], [0, 1, 2, 3, 4, 5, 6, 0]])
    def test_recurring_schedule_rejects_invalid_weekday_sets(self, days):
        with pytest.raises(ValidationError):
            PostSchedule(trigger="cron", time="09:00", days_of_week=days)

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
