"""Manual confirmation never republishes: durable queue state + ownership + audit."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api import database as database_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id
from api.routers import posts as posts_module

USER = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
PROFILE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
NOW = datetime.now(timezone.utc).isoformat()
SOURCE_JOB = "33333333-3333-3333-3333-333333333333"
LINK = "https://www.threads.net/@raffastudioproducoes/post/AbC123def"


@pytest.fixture()
def setup(monkeypatch, fake_db):
    db = fake_db({
        "posts": [{"id": 23, "user_id": USER, "profile_id": PROFILE,
                   "network": "threads", "text": "Teste"}],
        "publish_jobs": [{
            "id": SOURCE_JOB, "user_id": USER, "profile_id": PROFILE,
            "post_id": 23, "status": "unknown", "attempt": 1,
            "created_at": NOW, "started_at": NOW, "finished_at": NOW,
            "last_error": "Lease expirado durante publicacao",
            "external_id": None,
        }],
        "activities": [],
    })
    monkeypatch.setattr(database_module, "get_supabase", lambda: db)
    monkeypatch.setattr(posts_module, "log_action", lambda *a, **kw: actions.append((a, kw)))
    actions = []
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER
    app.dependency_overrides[get_current_profile_id] = lambda: PROFILE
    yield db, actions, TestClient(app)
    app.dependency_overrides.clear()


def test_unknown_queue_exposed_as_unknown_without_reenqueue(setup):
    _, _, _ = setup
    result = posts_module._get_last_publish_result(USER, 23, PROFILE)
    assert result["status"] == "unknown"
    assert result["job_id"] == SOURCE_JOB
    assert "Confirmação" in result["error"] or "confirmação" in result["error"].lower()


def test_manual_confirmation_records_proof_and_preserves_prior_error(setup, monkeypatch):
    db, actions, client = setup
    sent = []
    monkeypatch.setattr(posts_module, "run_scheduler_job", lambda *a: sent.append(a))
    response = client.post("/posts/23/reconcile", json={"permalink": LINK, "confirmed": True})
    assert response.status_code == 200
    assert response.json()["status"] == "manual_confirmed"
    row = db.tables["publish_jobs"][0]
    assert row["status"] == "succeeded"
    assert row["external_id"] == LINK
    assert "Lease expirado" in row["last_error"]
    assert "MANUAL_CONFIRMED" in row["last_error"]
    assert not sent
    assert actions[0][0][0] == "post_manual_reconciliation"
    result = posts_module._get_last_publish_result(USER, 23, PROFILE)
    assert result["status"] == "manual_confirmed"
    assert result["proof_url"] == LINK
    # A second confirmation cannot rewrite original audit or dispatch a second publication.
    assert client.post("/posts/23/reconcile", json={"permalink": LINK, "confirmed": True}).status_code == 409
    assert len(actions) == 1


@pytest.mark.parametrize("payload", [
    {"permalink": LINK, "confirmed": False},
    {"permalink": "https://evil.example/@user/post/Abcde", "confirmed": True},
    {"permalink": "http://www.threads.net/@user/post/Abcde", "confirmed": True},
    {"permalink": "https://www.threads.net/@user/post/Abcde?access_token=secret", "confirmed": True},
    {"permalink": "https://www.threads.net.evil.example/@user/post/Abcde", "confirmed": True},
])
def test_rejects_unverified_or_external_evidence(setup, payload):
    db, actions, client = setup
    assert client.post("/posts/23/reconcile", json=payload).status_code == 422
    assert db.tables["publish_jobs"][0]["status"] == "unknown"
    assert actions == []


def test_cannot_reconcile_other_users_posts(setup):
    db, _, client = setup
    app.dependency_overrides[get_current_user_id] = lambda: OTHER
    assert client.post("/posts/23/reconcile", json={"permalink": LINK, "confirmed": True}).status_code in (403, 404)
    assert db.tables["publish_jobs"][0]["status"] == "unknown"



def test_user_can_report_published_then_deleted_without_permalink(setup, monkeypatch):
    db, actions, client = setup
    scheduled = []
    monkeypatch.setattr(posts_module, "run_scheduler_job", lambda *args: scheduled.append(args))
    resp = client.post("/posts/23/reconcile", json={"reported_removed": True, "confirmed": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "reported_removed"
    job = db.tables["publish_jobs"][0]
    # Must not count as a provider-confirmed successful publication.
    assert job["status"] == "unknown"
    assert job["external_id"] is None
    assert job["finished_at"] == NOW
    assert job["last_error"].startswith("USER_REPORTED_REMOVED; ")
    assert "Lease expirado" in job["last_error"]
    assert not scheduled
    assert actions and actions[0][0][0] == "post_user_reported_published_removed"
    result = posts_module._get_last_publish_result(USER, 23, PROFILE)
    assert result["status"] == "reported_removed"
    assert not result.get("proof_url")
    # Repeating a report cannot rewrite audit or republish.
    assert client.post("/posts/23/reconcile", json={"reported_removed": True, "confirmed": True}).status_code == 409
    assert len(actions) == 1


@pytest.mark.parametrize("payload", [
    {"reported_removed": True, "confirmed": False},
    {"reported_removed": True, "confirmed": True, "permalink": LINK},
    {"reported_removed": False, "confirmed": True},
])
def test_reported_removed_requires_declaration_and_no_permalink(setup, payload):
    db, actions, client = setup
    assert client.post("/posts/23/reconcile", json=payload).status_code == 422
    assert db.tables["publish_jobs"][0]["status"] == "unknown"
    assert actions == []


def test_other_user_cannot_report_deleted_post(setup):
    db, actions, client = setup
    app.dependency_overrides[get_current_user_id] = lambda: OTHER
    response = client.post("/posts/23/reconcile", json={"reported_removed": True, "confirmed": True})
    assert response.status_code in (403, 404)
    assert db.tables["publish_jobs"][0]["last_error"] == "Lease expirado durante publicacao"
    assert actions == []


def _manual_retry_payload(**overrides):
    return {
        "source_job_id": SOURCE_JOB,
        "confirmed_not_published": True,
        "accepts_duplicate_risk": True,
        **overrides,
    }


def test_retry_unknown_threads_queues_once_without_calling_provider(setup, monkeypatch):
    db, actions, client = setup
    dispatches = []
    monkeypatch.setattr(posts_module, "run_scheduler_job", lambda *args: dispatches.append(args))
    calls = []

    def rpc(name, payload):
        calls.append((name, payload))
        assert name == "enqueue_manual_post_retry"
        assert payload["p_user_id"] == USER
        assert payload["p_profile_id"] == PROFILE
        assert payload["p_post_id"] == 23
        assert payload["p_source_job_id"] == SOURCE_JOB
        # A função SQL faz estas duas mudanças atomicamente.
        db.tables["publish_jobs"][0]["last_error"] = "MANUAL_RETRY_REQUESTED; original=Lease expirado"
        return MagicMock(execute=lambda: MagicMock(data="44444444-4444-4444-4444-444444444444"))

    monkeypatch.setattr(db, "rpc", rpc, raising=False)
    response = client.post("/posts/23/retry-unknown", json=_manual_retry_payload())
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    assert not dispatches  # somente enfileira, sem envio externo durante a requisição
    assert actions[0][0][0] == "post_manual_retry_requested"
    assert len(calls) == 1

    # Mesmo com a lista em cache, a segunda confirmação não cria nova tentativa.
    again = client.post("/posts/23/retry-unknown", json=_manual_retry_payload())
    assert again.status_code == 409
    assert len(calls) == 1
    assert client.post("/posts/23/reconcile", json={"permalink": LINK, "confirmed": True}).status_code == 409


@pytest.mark.parametrize("overrides", [
    {"confirmed_not_published": False},
    {"accepts_duplicate_risk": False},
    {"source_job_id": "not-a-uuid"},
])
def test_retry_unknown_requires_explicit_checks_and_valid_job_id(setup, monkeypatch, overrides):
    db, actions, client = setup
    calls = []
    monkeypatch.setattr(db, "rpc", lambda *a, **k: calls.append((a, k)), raising=False)
    response = client.post("/posts/23/retry-unknown", json=_manual_retry_payload(**overrides))
    assert response.status_code == 422
    assert not calls
    assert not actions


def test_retry_unknown_rejects_foreign_post_or_wrong_network(setup, monkeypatch):
    db, actions, client = setup
    calls = []
    monkeypatch.setattr(db, "rpc", lambda *a, **k: calls.append((a, k)), raising=False)
    app.dependency_overrides[get_current_user_id] = lambda: OTHER
    assert client.post("/posts/23/retry-unknown", json=_manual_retry_payload()).status_code in (403, 404)
    app.dependency_overrides[get_current_user_id] = lambda: USER
    db.tables["posts"][0]["network"] = "facebook"
    assert client.post("/posts/23/retry-unknown", json=_manual_retry_payload()).status_code == 422
    assert not calls
    assert not actions


def test_retry_unknown_rejects_stale_source_or_removed_report(setup, monkeypatch):
    db, actions, client = setup
    calls = []
    monkeypatch.setattr(db, "rpc", lambda *a, **k: calls.append((a, k)), raising=False)
    stale = client.post("/posts/23/retry-unknown", json=_manual_retry_payload(
        source_job_id="22222222-3333-4444-5555-666666666666"))
    assert stale.status_code == 409
    db.tables["publish_jobs"][0]["last_error"] = "USER_REPORTED_REMOVED; original=Lease expirado"
    assert client.post("/posts/23/retry-unknown", json=_manual_retry_payload()).status_code == 409
    assert not calls
    assert not actions


def test_retry_unknown_rpc_failure_does_not_claim_success(setup, monkeypatch):
    db, actions, client = setup

    def failing_rpc(*a, **k):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(db, "rpc", failing_rpc, raising=False)
    assert client.post("/posts/23/retry-unknown", json=_manual_retry_payload()).status_code == 503
    assert db.tables["publish_jobs"][0]["status"] == "unknown"
    assert not actions


def test_manual_retry_pending_has_visible_status(setup):
    db, _, _ = setup
    row = db.tables["publish_jobs"][0]
    row.update({
        "status": "pending",
        "idempotency_key": "manual_retry:" + SOURCE_JOB,
        "created_at": NOW,
    })
    assert posts_module._get_last_publish_result(USER, 23, PROFILE)["status"] == "retry_pending"
