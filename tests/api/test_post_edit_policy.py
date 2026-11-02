"""Contrato R12: só ocorrências futuras e fora da janela de 30 minutos."""
from datetime import datetime, timedelta, timezone

import pytest

from api.post_edit_policy import occurrence_edit_window


def test_future_slot_more_than_thirty_minutes_is_editable():
    now = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
    assert occurrence_edit_window(now + timedelta(minutes=31), now=now).allowed


@pytest.mark.parametrize("minutes", [30, 29, 0, -1])
def test_freeze_at_thirty_minutes_and_past(minutes):
    now = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
    result = occurrence_edit_window(now + timedelta(minutes=minutes), now=now)
    assert not result.allowed
    assert result.locked_at == now + timedelta(minutes=minutes - 30)


@pytest.mark.parametrize("state", [
    "running", "succeeded", "published", "failed", "unknown",
    "cancelled", "paused",
])
def test_completed_inflight_or_uncertain_occurrences_are_never_editable(state):
    now = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
    assert not occurrence_edit_window(
        now + timedelta(days=2), now=now, status=state,
    ).allowed


def test_claim_always_blocks_even_if_far_in_future():
    now = datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc)
    assert not occurrence_edit_window(
        now + timedelta(days=1), now=now, claimed=True,
    ).allowed


def test_timezone_comparison_is_in_utc():
    from zoneinfo import ZoneInfo
    brazil = ZoneInfo("America/Sao_Paulo")
    scheduled_at = datetime(2026, 11, 2, 15, 30, tzinfo=brazil)
    now = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
    assert not occurrence_edit_window(scheduled_at, now=now).allowed
    assert occurrence_edit_window(scheduled_at, now=now - timedelta(seconds=1)).allowed


def test_naive_datetime_is_rejected():
    aware = datetime(2026, 11, 2, 14, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        occurrence_edit_window(aware.replace(tzinfo=None), now=aware)
    with pytest.raises(ValueError):
        occurrence_edit_window(aware, now=aware.replace(tzinfo=None))
