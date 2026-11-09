"""Contrato do calendário de campanhas: 30 dias ativos, janela e rotação.

Testes puramente locais: não criam jobs, posts ou chamadas externas.
"""
from datetime import date, time
from zoneinfo import ZoneInfo

import pytest

from api.campaign_schedule import count_campaign_days, plan_campaign_slots


def plan(**overrides):
    data = {
        "start_date": date(2026, 11, 10),  # terça
        "end_date": date(2026, 11, 11),
        "weekdays": [1, 2],
        "start_time": time(9, 0),
        "end_time": time(18, 0),
        "posts_per_day": 4,
        "item_ids": [101, 102, 103, 104, 105],
    }
    data.update(overrides)
    return plan_campaign_slots(**data)


def test_one_product_per_slot_with_wraparound_and_unique_index():
    slots = plan()
    assert len(slots) == 8
    assert [s.occurrence_index for s in slots] == list(range(8))
    assert [s.item_id for s in slots] == [101, 102, 103, 104, 105, 101, 102, 103]
    assert [s.local_at.strftime("%H:%M") for s in slots] == [
        "09:00", "12:00", "15:00", "18:00",
        "09:00", "12:00", "15:00", "18:00",
    ]


def test_210_calendar_days_inclusive_are_allowed_but_211_rejected():
    slots = plan(
        start_date=date(2026, 11, 2),
        end_date=date(2027, 5, 30),
        weekdays=list(range(7)),
        start_time=time(9),
        end_time=time(9),
        posts_per_day=1,
    )
    assert len(slots) == 210
    with pytest.raises(ValueError, match="210 dias"):
        plan(
            start_date=date(2026, 11, 2),
            end_date=date(2027, 5, 31),
        )


def test_selected_weekday_count_matches_calendar_example():
    assert count_campaign_days(
        date(2026, 11, 1), date(2026, 11, 30), [0, 2, 4, 6],
    ) == 18


def test_daily_quantity_is_evenly_spread_including_end_time():
    slots = plan(end_date=date(2026, 11, 10), end_time=time(10, 30), posts_per_day=2)
    assert [slot.local_at.strftime("%H:%M") for slot in slots] == ["09:00", "10:30"]


def test_empty_weekdays_and_products_are_invalid():
    with pytest.raises(ValueError, match="dias da semana"):
        plan(weekdays=[])
    with pytest.raises(ValueError, match="produto"):
        plan(item_ids=[])


def test_no_matching_weekdays_returns_no_slots():
    assert plan(weekdays=[0]) == []


@pytest.mark.parametrize("bad", [
    {"end_date": date(2026, 11, 9)},
    {"posts_per_day": 0},
    {"posts_per_day": 16},
    {"start_time": time(18), "end_time": time(9)},
    {"weekdays": [7]},
])
def test_invalid_time_windows_or_configuration_are_rejected(bad):
    with pytest.raises(ValueError):
        plan(**bad)


def test_brasilia_timezone_is_used_and_utc_is_unambiguous():
    first = plan(end_date=date(2026, 11, 10))[0]
    assert first.local_at.tzinfo == ZoneInfo("America/Sao_Paulo")
    assert first.local_at.isoformat() == "2026-11-10T09:00:00-03:00"
    assert first.utc_at.isoformat() == "2026-11-10T12:00:00+00:00"


def test_nonexistent_historical_brasilia_hour_is_rejected():
    # Em 2018-11-04 o relógio brasileiro saltou meia-noite (início do DST).
    with pytest.raises(ValueError, match="fuso"):
        plan(
            start_date=date(2018, 11, 4),
            end_date=date(2018, 11, 4),
            weekdays=[6],
            start_time=time(0),
            end_time=time(0),
            posts_per_day=1,
        )


def test_one_or_fifteen_daily_posts_and_oversized_count():
    first = plan(end_date=date(2026, 11, 10), posts_per_day=1)
    assert [s.local_at.strftime("%H:%M") for s in first] == ["09:00"]
    fifteen = plan(end_date=date(2026, 11, 10), posts_per_day=15)
    assert len(fifteen) == 15
    assert fifteen[0].local_at.strftime("%H:%M") == "09:00"
    assert fifteen[-1].local_at.strftime("%H:%M") == "18:00"
    assert len({s.local_at for s in fifteen}) == 15
    with pytest.raises(ValueError, match="1 e 15"):
        plan(posts_per_day=16)


def test_multiple_posts_require_sufficient_daily_window():
    with pytest.raises(ValueError, match="janela diária"):
        plan(start_time=time(9), end_time=time(9), posts_per_day=2)
    with pytest.raises(ValueError, match="janela diária"):
        plan(start_time=time(9), end_time=time(9, 5), posts_per_day=15)
