"""Regressões do publicador X usando o OAuth global da plataforma."""

import sys
from datetime import datetime, timedelta, timezone

import shopee_bot.scheduler.bot_post_x  # noqa: F401
from shopee_bot.database.activity_types import ActivityType


module = sys.modules["shopee_bot.scheduler.bot_post_x"]


def test_expired_x_token_refreshes_with_global_oauth_and_scopes_saved_tokens(monkeypatch):
    """A luz e o scheduler devem usar o mesmo X_CLIENT_ID/X_CLIENT_SECRET."""
    profile_id = "profile-7"
    refreshed = []
    published = []
    activities = []

    monkeypatch.setattr(
        module.schedulers,
        "get_by_id",
        lambda job_id: {"user_id": 42, "post_id": 9, "profile_id": profile_id},
    )
    monkeypatch.setattr(
        module.x_credentials,
        "get_by_user_id",
        lambda user_id, profile_id=None: {
            "username": "cliente",
            "x_access_token": "expired-access-token",
            "x_refresh_token": "refresh-token",
            "token_expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
            # Valores legados propositalmente diferentes do app OAuth global.
            "x_app_id": "legacy-client-id",
            "x_secret": "legacy-client-secret",
        },
    )
    monkeypatch.setattr(
        module.posts, "get", lambda user_id, post_id, saved_profile_id: [{"text": "teste"}]
    )
    async def refresh_access_token(token):
        assert token == "refresh-token"
        return {"access_token": "fresh-access-token", "refresh_token": "fresh-refresh-token"}

    monkeypatch.setattr(module.x_oauth, "refresh_access_token", refresh_access_token)
    monkeypatch.setattr(
        module.x_credentials,
        "update_tokens",
        lambda user_id, saved_profile_id, tokens: refreshed.append((user_id, saved_profile_id, tokens)),
    )
    monkeypatch.setattr(
        module.XAPI,
        "post_text",
        lambda access_token, text, reply_to_id=None: published.append((access_token, text)) or {"id": "x-1"},
    )
    monkeypatch.setattr(
        module,
        "insert_activities",
        lambda user_id, activity_type, metadata, profile_id=None: activities.append(
            (user_id, activity_type, metadata, profile_id)
        ),
    )

    module.bot_post_x("job-1")

    assert refreshed == [
        (42, profile_id, {"access_token": "fresh-access-token", "refresh_token": "fresh-refresh-token"})
    ]
    assert published == [("fresh-access-token", "teste")]
    assert activities[0][1] == ActivityType.BOT_POST_SUCCESS
