"""CronTrigger no fuso da agenda: instante UTC certo, com e sem horario de verao.

Regressao: linha sem fuso ou com America/Sao_Paulo dispara exatamente como antes
(trigger sem `timezone`, herdando o fuso fixo do scheduler).
"""

from datetime import datetime, time, timezone as dt_timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import pytz
from apscheduler.triggers.cron import CronTrigger

import shopee_bot.scheduler as scheduler
from shopee_bot.scheduler import central_reconciler
from shopee_bot.database import schedulers

UTC = dt_timezone.utc
LEGACY_SCHEDULER_TZ = pytz.timezone("America/Sao_Paulo")


class CaptureScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, **kwargs):
        self.jobs.append(kwargs)


def _cron_kwargs(monkeypatch, timezone_name):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "false")
    monkeypatch.setattr(scheduler.schedulers, "insert", lambda *_args: "sched-1")
    fake = CaptureScheduler()
    monkeypatch.setattr(scheduler, "_scheduler", fake)
    job = {
        "post_id": 1, "func": "bot_post", "trigger": "cron", "profile_id": "p-1",
        "time": time(10, 0), "day_of_week": 0, "days_of_week": [0, 1, 2, 3, 4, 5, 6],
    }
    if timezone_name is not None:
        job["timezone"] = timezone_name
    scheduler._add_job("u-1", job, conn=None)
    return fake.jobs[0]


def _next_fire_utc(kwargs, after_utc, default_tz=LEGACY_SCHEDULER_TZ):
    trigger = CronTrigger(
        minute=kwargs["minute"], hour=kwargs["hour"], day_of_week=kwargs["day_of_week"],
        start_date=kwargs.get("start_date"), timezone=kwargs.get("timezone") or default_tz,
    )
    return trigger.get_next_fire_time(None, after_utc).astimezone(UTC)


@pytest.mark.parametrize("timezone_name, after, expected", [
    # Brasilia: UTC-3 o ano todo (sem horario de verao desde 2019).
    ("America/Sao_Paulo", datetime(2026, 7, 1, 0, 0, tzinfo=UTC), datetime(2026, 7, 1, 13, 0, tzinfo=UTC)),
    ("America/Sao_Paulo", datetime(2026, 1, 15, 0, 0, tzinfo=UTC), datetime(2026, 1, 15, 13, 0, tzinfo=UTC)),
    # Lisboa: verao UTC+1, inverno UTC+0.
    ("Europe/Lisbon", datetime(2026, 7, 1, 0, 0, tzinfo=UTC), datetime(2026, 7, 1, 9, 0, tzinfo=UTC)),
    ("Europe/Lisbon", datetime(2026, 1, 15, 0, 0, tzinfo=UTC), datetime(2026, 1, 15, 10, 0, tzinfo=UTC)),
    # Toquio: UTC+9 fixo; 10:00 local = 01:00 UTC do mesmo dia.
    ("Asia/Tokyo", datetime(2026, 7, 1, 0, 0, tzinfo=UTC), datetime(2026, 7, 1, 1, 0, tzinfo=UTC)),
    # Nova York: vespera (EST UTC-5) e dia da mudanca 08/03/2026 (EDT UTC-4).
    ("America/New_York", datetime(2026, 3, 7, 12, 0, tzinfo=UTC), datetime(2026, 3, 7, 15, 0, tzinfo=UTC)),
    ("America/New_York", datetime(2026, 3, 8, 12, 0, tzinfo=UTC), datetime(2026, 3, 8, 14, 0, tzinfo=UTC)),
])
def test_local_10h_fires_at_correct_utc_instant(monkeypatch, timezone_name, after, expected):
    kwargs = _cron_kwargs(monkeypatch, timezone_name)
    assert kwargs["timezone"] == timezone_name
    assert _next_fire_utc(kwargs, after) == expected


@pytest.mark.parametrize("timezone_name", [None, "America/Sao_Paulo", "Invalida/Zona"])
def test_rows_without_or_with_brasilia_timezone_keep_legacy_schedule(monkeypatch, timezone_name):
    kwargs = _cron_kwargs(monkeypatch, timezone_name)
    assert kwargs["timezone"] == "America/Sao_Paulo"
    legacy = {key: value for key, value in kwargs.items() if key != "timezone"}
    for after in (datetime(2026, 1, 15, tzinfo=UTC), datetime(2026, 7, 1, tzinfo=UTC)):
        # Trigger antigo: sem `timezone`, herda pytz America/Sao_Paulo do scheduler.
        assert _next_fire_utc(kwargs, after) == _next_fire_utc(legacy, after, LEGACY_SCHEDULER_TZ)


def test_insert_persists_validated_timezone(monkeypatch):
    seen = []
    monkeypatch.setattr(schedulers, "execute_db", lambda query, args, conn=None: seen.append((query, args)))
    base = {"post_id": 1, "func": "bot_post", "trigger": "cron", "profile_id": "p-1"}
    schedulers.insert("u-1", {**base, "timezone": "Asia/Tokyo"})
    schedulers.insert("u-1", base)
    columns = [name.strip() for name in seen[0][0].split("(", 1)[1].split(")", 1)[0].split(",")]
    position = columns.index("timezone")
    assert seen[0][1][position] == "Asia/Tokyo"
    assert seen[1][1][position] == "America/Sao_Paulo"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 7, 1, 13, 0, tzinfo=UTC).astimezone(tz)


def test_occurrence_key_regression_and_row_timezone(monkeypatch):
    monkeypatch.setattr(scheduler, "datetime", FrozenDatetime)
    instant = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)
    legacy_key = "j:" + instant.astimezone(LEGACY_SCHEDULER_TZ).strftime("%Y-%m-%dT%H:%M")
    assert legacy_key == "j:2026-07-01T10:00"
    assert scheduler._occurrence_key("j", {"trigger": "cron"}) == legacy_key
    assert scheduler._occurrence_key("j", {"trigger": "cron", "timezone": "America/Sao_Paulo"}) == legacy_key
    assert scheduler._occurrence_key("j", {"trigger": "cron", "timezone": "Asia/Tokyo"}) == "j:2026-07-01T22:00"
    assert scheduler._occurrence_key("j", {"trigger": "date", "timezone": "Asia/Tokyo"}) == "j"


def test_central_reconciler_mirror_uses_row_timezone(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("SCHEDULER_ENVIRONMENT", "production")
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")
    rows = [
        {"id": "a", "dispatch_revision": 1, "trigger": "cron", "time": time(10, 0),
         "days_of_week": [0], "day_of_week": 0, "start_date": None, "timezone": "Europe/Lisbon"},
        {"id": "b", "dispatch_revision": 1, "trigger": "cron", "time": time(10, 0),
         "days_of_week": [0], "day_of_week": 0, "start_date": None},
    ]
    monkeypatch.setattr(schedulers, "list_central_dispatch_jobs", lambda: rows)
    created = []
    fake = SimpleNamespace(
        get_job=lambda *_a, **_k: None, get_jobs=lambda **_k: [],
        add_job=lambda **kwargs: created.append(kwargs),
    )
    central_reconciler.reconcile(fake, lambda _id: None)
    assert [job["timezone"] for job in created] == ["Europe/Lisbon", "America/Sao_Paulo"]
    assert ZoneInfo(created[0]["timezone"])
