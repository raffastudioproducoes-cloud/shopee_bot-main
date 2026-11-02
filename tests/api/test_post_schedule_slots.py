"""Contratos isolados: produto único, status real por horário e privacidade."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from api.routers import posts as module


def test_one_product_only_rejects_before_database():
    with pytest.raises(HTTPException) as error:
        module._validate_product_ids(7, [1, 2])
    assert error.value.status_code == 422


def test_public_error_has_no_provider_payload():
    raw = {"status": "failed", "at": "2026-11-01T18:00:12Z",
           "error": "Status:403 URL:https://example.test?access_token=secret"}
    assert module._public_publish_result(raw, False)["error"] == "Falha ao publicar. Confira o horário da execução."
    assert module._public_publish_result(raw, True)["error"] == raw["error"]


def test_cron_occurrence_is_mapped_to_actual_weekday_and_time(monkeypatch):
    fake = MagicMock()
    query = fake.table.return_value
    for method in ("select", "eq", "order", "limit"):
        getattr(query, method).return_value = query
    query.execute.return_value.data = [{
        "scheduler_id": "cron-one",
        "idempotency_key": "cron-one:2026-11-02T18:00",
        "status": "failed", "created_at": "2026-11-02T21:00:00Z",
        "finished_at": "2026-11-02T21:00:12Z", "last_error": "403",
    }]
    monkeypatch.setattr(module, "supabase", fake)
    monkeypatch.setattr(module, "scope_owner", lambda query, *_args: query)
    entries = [{"id": "cron-one", "trigger": "cron", "days_of_week": [0, 2], "time": "18:00:00"}]
    slots = module._schedule_slot_history(1, 2, "profile", entries, False)
    assert [(item["day_of_week"], item["time"], item["status"]) for item in slots] == [
        (0, "18:00", "erro"), (2, "18:00", "programado"),
    ]
    assert slots[0]["error"] is None
    assert "2026-11-02" in slots[0]["last_at"]


def test_old_403_is_failure_only_with_first_part_and_same_scheduler():
    job = {
        "scheduler_id": "cron-one", "status": "unknown",
        "started_at": "2026-11-01T21:00:00Z",
        "finished_at": "2026-11-01T21:00:12Z",
    }
    activity = {
        "activity_id": 2, "created_at": "2026-11-01T21:00:10Z",
        "metadata": {
            "job_id": "cron-one", "published_parts": 0,
            "error": "Failed to Create Media Container:\\nStatus: 403\\nURL: https://graph.threads.net/",
        },
    }
    assert module._confirmed_legacy_container_rejection(activity, job)
    assert not module._confirmed_legacy_container_rejection(
        {**activity, "metadata": {**activity["metadata"], "published_parts": 1}}, job
    )
    assert not module._confirmed_legacy_container_rejection(
        {**activity, "metadata": {**activity["metadata"], "job_id": "other"}}, job
    )
    assert not module._confirmed_legacy_container_rejection(
        {**activity, "metadata": {**activity["metadata"],
                                  "error": "Failed to Publish Media Container: Status: 403"}}, job
    )
