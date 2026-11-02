"""
Multi-perfil no lado Flask/scheduler: o job guarda o perfil do post e o bot
usa a credencial DESSE perfil; job antigo (sem perfil) segue como antes.
Tudo mockado (sem banco nem rede).
"""

import sys
import importlib

import pytest

import shopee_bot.scheduler.bot_post_instagram  # noqa: F401
from shopee_bot.database import (
    activities, facebook_credentials, instagram_credentials, kwai_credentials,
    posts, schedulers, shopee_credentials, threads_credentials, tiktok_credentials,
    x_credentials,
)
update_products_module = importlib.import_module("shopee_bot.scheduler.update_products")

bot = sys.modules["shopee_bot.scheduler.bot_post_instagram"]

CREDENTIAL_MODULES = [
    facebook_credentials, instagram_credentials, kwai_credentials,
    threads_credentials, tiktok_credentials, x_credentials,
]


def test_scheduler_insert_persists_profile_id(monkeypatch):
    captured = {}
    monkeypatch.setattr(schedulers, "execute_db", lambda q, args, conn=None: captured.update(q=q, args=args))
    schedulers.insert(
        "user-1",
        {"post_id": 7, "func": "bot_post", "trigger": "date", "profile_id": "profile-a"},
    )
    assert "profile_id" in captured["q"]
    assert captured["args"][-1] == "profile-a"


def test_scheduler_insert_persists_recurring_weekdays(monkeypatch):
    captured = {}
    monkeypatch.setattr(schedulers, "execute_db", lambda q, args, conn=None: captured.update(q=q, args=args))

    schedulers.insert(
        "user-1",
        {
            "post_id": 7,
            "func": "bot_post",
            "trigger": "cron",
            "day_of_week": 1,
            "days_of_week": [1, 3, 5],
            "profile_id": "profile-a",
        },
    )

    assert "days_of_week" in captured["q"]
    assert captured["args"][-1] == "profile-a"
    assert captured["args"][6] == [1, 3, 5]


def test_every_credential_lookup_can_be_scoped_by_profile(monkeypatch):
    for module in CREDENTIAL_MODULES:
        captured = {}
        monkeypatch.setattr(
            module, "query_db", lambda q, args, one=False, _c=captured: _c.update(q=q, args=args)
        )
        module.get_by_user_id("user-1", "profile-a")
        assert "profile_id = %s::uuid" in captured["q"], module.__name__
        expected_args = (
            ("profile-a", "user-1")
            if module in (x_credentials, tiktok_credentials)
            else ("profile-a", "profile-a", "user-1")
        )
        assert captured["args"] == expected_args


def test_shopee_credential_lookup_is_shared_by_account(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        shopee_credentials, "query_db", lambda q, args, one=False: captured.update(q=q, args=args)
    )

    shopee_credentials.get_by_user_id("user-1")

    assert "profile_id" not in captured["q"]
    assert captured["args"] == ("user-1",)


def test_scheduler_post_query_requires_the_jobs_profile(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        posts, "query_db", lambda query, args: captured.update(query=query, args=args)
    )

    posts.get("user-1", 7, "profile-a")

    assert "profile_id = %s::uuid" in captured["query"]
    assert captured["args"] == (7, "user-1", "profile-a", "user-1", "profile-a")
    assert "p.user_id = %s" in captured["query"]
    assert "p.profile_id = %s::uuid" in captured["query"]


def test_shopee_refresh_requires_profile_but_reads_shared_catalog(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        update_products_module.shopee_credentials,
        "get_by_user_id",
        lambda user_id: captured.update(credential=user_id) or {
            "username": "cliente", "shopee_app_id": None, "shopee_secret": None,
            "shopee_status": False,
        },
    )

    with pytest.raises(RuntimeError, match="profile_id"):
        update_products_module.update_products("user-1", None)

    update_products_module.update_products("user-1", "profile-a")
    assert captured["credential"] == "user-1"

def _run_bot(monkeypatch, job):
    seen = {}
    monkeypatch.setattr(bot.schedulers, "get_by_id", lambda job_id: job)

    def fake_creds(user_id, profile_id=None):
        seen["creds_profile"] = profile_id
        return {
            "username": "fulano", "instagram_app_id": "a", "instagram_secret": "s",
            "instagram_user_access_token": "t", "instagram_ig_user_id": "ig",
        }

    monkeypatch.setattr(bot.instagram_credentials, "get_by_user_id", fake_creds)
    monkeypatch.setattr(bot.posts, "get", lambda u, p, profile_id: [{"text": "oi", "product_ids": []}])
    monkeypatch.setattr(bot.InstagramAPI, "post_text", lambda *a, **k: "media-1")

    def fake_activity(user_id, activity_type, metadata, profile_id=None):
        seen["activity_profile"] = profile_id

    monkeypatch.setattr(bot, "insert_activities", fake_activity)
    bot.bot_post_instagram("job-1")
    return seen


def test_bot_uses_credential_and_activity_of_the_jobs_profile(monkeypatch):
    seen = _run_bot(monkeypatch, {"user_id": 42, "post_id": 7, "profile_id": "profile-a"})
    assert seen == {"creds_profile": "profile-a", "activity_profile": "profile-a"}


def test_bot_rejects_legacy_job_without_profile(monkeypatch):
    with pytest.raises(RuntimeError, match="profile_id"):
        _run_bot(monkeypatch, {"user_id": 42, "post_id": 7})


def test_insert_activities_persists_profile_id(monkeypatch):
    captured = {}
    monkeypatch.setattr(activities, "execute_db", lambda q, args, conn=None: captured.update(q=q, args=args))
    from shopee_bot.database.activity_types import ActivityType

    activities.insert_activities(
        "user-1", ActivityType.BOT_POST_SUCCESS, {"metadata": {}}, profile_id="profile-a"
    )
    assert "profile_id" in captured["q"] and captured["args"][-1] == "profile-a"
