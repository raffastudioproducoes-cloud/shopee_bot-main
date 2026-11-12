"""Slot de campanha que falhou por credencial: retentativa única dentro de 60 min."""
import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("APP_ENCRYPTION_KEY", "e7lc8f3AsY0VNg7Kpy1K5umJirUK6jwqkJg7_xhn0IY=")
os.environ.setdefault("API_SECRET_KEY", "test-only-api-secret-key-0123456789abcdef-0123456789abcdef-padding-64b")

from shopee_bot.scheduler import campaign_dispatch

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(monkeypatch):
    state = {"updates": 0, "job": {}}

    def fake_query_db(sql, args=(), one=False):
        if sql.lstrip().startswith("SELECT"):
            return state["job"]
        state["updates"] += 1
        return {"publish_job_id": "j1"}

    monkeypatch.setattr(campaign_dispatch, "query_db", fake_query_db)

    def set_job(minutes_late=10, **over):
        state["job"] = dict(
            status="failed", attempt=1, external_id=None, external_started_at=None,
            scheduled_for=NOW - timedelta(minutes=minutes_late), db_now=NOW,
        )
        state["job"].update(over)
    state["set_job"] = set_job
    return state


def test_credential_failure_within_60min_requeues(db):
    db["set_job"](minutes_late=30)
    assert campaign_dispatch.retry_credential_failure("j1") is True
    assert db["updates"] == 1


def test_credential_failure_after_60min_stays_failed(db):
    db["set_job"](minutes_late=61)
    assert campaign_dispatch.retry_credential_failure("j1") is False
    assert db["updates"] == 0


@pytest.mark.parametrize("over", [
    {"status": "succeeded"},
    {"external_id": "abc123"},
    {"external_started_at": NOW},
])
def test_already_published_is_never_requeued(db, over):
    db["set_job"](**over)
    assert campaign_dispatch.retry_credential_failure("j1") is False
    assert db["updates"] == 0


def test_two_attempts_already_made_stays_failed(db):
    db["set_job"](attempt=2)
    assert campaign_dispatch.retry_credential_failure("j1") is False
    assert db["updates"] == 0
