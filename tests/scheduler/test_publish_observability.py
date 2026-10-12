"""Rastreabilidade segura das tentativas de publicação.

Os detalhes técnicos são úteis ao administrador, mas nunca podem persistir
tokens, senhas, segredos ou chaves recebidos em uma exceção de provedor.
"""

from shopee_bot.database import activities
from shopee_bot.database.activity_types import ActivityType


def test_publish_failure_is_sanitized_before_activity_and_business_log(monkeypatch):
    persisted = []
    business_logs = []

    monkeypatch.setattr(activities, "Jsonb", lambda value: value)
    monkeypatch.setattr(
        activities,
        "execute_db",
        lambda query, args, open_conn=None: persisted.append(args) or 99,
    )
    monkeypatch.setattr(
        activities,
        "_log_action",
        lambda *args, **kwargs: business_logs.append((args, kwargs)),
    )

    activities.insert_activities(
        "user-1",
        ActivityType.BOT_POST_FAILURE,
        {
            "metadata": {
                "network": "x",
                "job_id": "job-7",
                "post_id": 42,
                "stage": "publish",
                "error": "401 token=top-secret Authorization: Bearer abc.def-ghi",
            }
        },
        profile_id="profile-1",
    )

    stored = persisted[0][0]
    assert "top-secret" not in stored["error"]
    assert "abc.def-ghi" not in stored["error"]
    assert stored["network"] == "x"
    assert business_logs == [
        (
            (
                "post_publish_failed",
                "network=x post_id=42 job_id=job-7 stage=publish "
                "error=401 token=***REDACTED*** Authorization: Bearer ***REDACTED***",
            ),
            {"user_id": "user-1", "profile_id": "profile-1"},
        )
    ]


def test_publish_success_is_written_to_business_log_with_trace_ids(monkeypatch):
    business_logs = []
    monkeypatch.setattr(activities, "Jsonb", lambda value: value)
    monkeypatch.setattr(activities, "execute_db", lambda *args, **kwargs: 100)
    monkeypatch.setattr(
        activities,
        "_log_action",
        lambda *args, **kwargs: business_logs.append((args, kwargs)),
    )

    activities.insert_activities(
        "user-2",
        ActivityType.BOT_POST_SUCCESS,
        {"metadata": {"network": "facebook", "job_id": "job-9", "post_id": 17, "stage": "publish"}},
        profile_id="profile-2",
    )

    assert business_logs == [
        (
            ("post_publish_succeeded", "network=facebook post_id=17 job_id=job-9 stage=publish"),
            {"user_id": "user-2", "profile_id": "profile-2"},
        )
    ]
