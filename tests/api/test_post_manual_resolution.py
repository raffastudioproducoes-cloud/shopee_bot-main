"""Decisão humana sobre 'sem confirmação' em qualquer rede, e reenvio manual de 'failed'.

Nunca reenvia sozinho, nunca mexe na cota, só o dono decide, uma decisão por ocorrência.
"""
from datetime import datetime, timezone

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
SCHEDULER = "44444444-4444-4444-4444-444444444444"
SOURCE_JOB = "33333333-3333-3333-3333-333333333333"
NOW = datetime.now(timezone.utc).isoformat()


def _quota_must_not_move(*_args, **_kwargs):
    raise AssertionError("decisão manual não pode reservar nem devolver cota")


@pytest.fixture()
def world(monkeypatch, fake_db):
    def build(network="facebook", status="unknown", origin="legacy", last_error="Timeout lendo resposta"):
        db = fake_db({
            "posts": [{"id": 23, "user_id": USER, "profile_id": PROFILE, "network": network,
                       "text": "Oferta", "publication_origin": origin}],
            "publish_jobs": [{
                "id": SOURCE_JOB, "scheduler_id": SCHEDULER, "user_id": USER, "profile_id": PROFILE,
                "post_id": 23, "status": status, "attempt": 1, "idempotency_key": SCHEDULER,
                "created_at": NOW, "started_at": NOW, "finished_at": NOW,
                "last_error": last_error, "external_id": None,
            }],
            "activities": [],
        })
        monkeypatch.setattr(database_module, "get_supabase", lambda: db)
        monkeypatch.setattr(posts_module, "log_action", lambda *a, **kw: actions.append(a[0]))
        monkeypatch.setattr(posts_module, "reserve_post_plan_quota", _quota_must_not_move)
        monkeypatch.setattr(posts_module, "release_failed_post_plan_quota", _quota_must_not_move)
        monkeypatch.setattr(posts_module, "run_scheduler_job",
                            lambda *a: (_ for _ in ()).throw(AssertionError("não pode publicar na request")))
        return db

    actions = []
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: USER
    app.dependency_overrides[get_current_profile_id] = lambda: PROFILE
    yield build, actions, TestClient(app)
    app.dependency_overrides.clear()


def _resolve(client, outcome, **extra):
    return client.post("/posts/23/resolve-unknown", json={
        "source_job_id": SOURCE_JOB, "outcome": outcome, "confirmed": True, **extra})


def test_confirmo_que_foi_publicado_fecha_como_sucesso_sem_reenviar(world):
    build, actions, client = world
    db = build()
    resp = _resolve(client, "published")
    assert resp.status_code == 200 and resp.json()["status"] == "manual_confirmed"
    job = db.tables["publish_jobs"][0]
    assert job["status"] == "succeeded"
    assert job["last_error"].startswith("MANUAL_CONFIRMED; ") and "Timeout lendo resposta" in job["last_error"]
    assert len(db.tables["publish_jobs"]) == 1  # nada novo na fila
    result = posts_module._get_last_publish_result(USER, 23, PROFILE)
    assert result["status"] == "manual_confirmed" and "proof_url" not in result
    activity = db.tables["activities"][-1]
    assert activity["activity_id"] == 10 and activity["user_id"] == USER
    assert activity["metadata"]["decision"] == "published"
    assert activity["metadata"]["decided_by"] == USER and activity["metadata"]["decided_at"]
    assert actions == ["post_manual_resolution"]


def test_nao_foi_publicado_vira_failed_e_libera_reenvio(world):
    build, _, client = world
    db = build()
    resp = _resolve(client, "not_published")
    assert resp.status_code == 200 and resp.json()["status"] == "failed"
    job = db.tables["publish_jobs"][0]
    assert job["status"] == "failed" and job["last_error"].startswith("MANUAL_NOT_PUBLISHED; ")
    result = posts_module._public_publish_result(
        posts_module._get_last_publish_result(USER, 23, PROFILE), is_admin=False)
    assert result["status"] == "failed" and result["job_id"] == SOURCE_JOB
    assert result["manual_not_published"] is True and "não publicado" in result["error"]

    retry = client.post("/posts/23/retry-failed", json={"source_job_id": SOURCE_JOB, "confirmed": True})
    assert retry.status_code == 202
    new_jobs = [row for row in db.tables["publish_jobs"] if row["id"] != SOURCE_JOB]
    assert len(new_jobs) == 1
    assert new_jobs[0]["idempotency_key"] == f"manual_retry:{SOURCE_JOB}"
    assert new_jobs[0]["scheduler_id"] == SCHEDULER and new_jobs[0]["network"] == "facebook"
    assert [a["metadata"]["decision"] for a in db.tables["activities"]] == ["not_published", "retry_requested"]


def test_decisao_e_unica_por_ocorrencia(world):
    build, actions, client = world
    build()
    assert _resolve(client, "published").status_code == 200
    assert _resolve(client, "not_published").status_code == 409
    assert _resolve(client, "published").status_code == 409
    assert actions == ["post_manual_resolution"]


def test_reenvio_duplo_da_mesma_falha_e_bloqueado(world):
    build, _, client = world
    db = build(status="failed", last_error="Threads: contêiner c1 terminou como ERROR")
    body = {"source_job_id": SOURCE_JOB, "confirmed": True}
    assert client.post("/posts/23/retry-failed", json=body).status_code == 202
    assert client.post("/posts/23/retry-failed", json=body).status_code == 409
    assert len(db.tables["publish_jobs"]) == 2


@pytest.mark.parametrize("status", ["unknown", "succeeded", "running", "pending"])
def test_reenvio_so_para_failed(world, status):
    build, _, client = world
    db = build(status=status)
    resp = client.post("/posts/23/retry-failed", json={"source_job_id": SOURCE_JOB, "confirmed": True})
    assert resp.status_code == 409
    assert len(db.tables["publish_jobs"]) == 1


def test_unknown_nunca_e_reenviado_sem_decisao(world):
    build, _, client = world
    db = build(status="unknown")
    assert client.post("/posts/23/retry-failed", json={"source_job_id": SOURCE_JOB, "confirmed": True}).status_code == 409
    assert db.tables["publish_jobs"][0]["status"] == "unknown"


def test_exige_confirmacao_explicita(world):
    build, actions, client = world
    db = build()
    resp = client.post("/posts/23/resolve-unknown", json={
        "source_job_id": SOURCE_JOB, "outcome": "published", "confirmed": False})
    assert resp.status_code == 422
    assert db.tables["publish_jobs"][0]["status"] == "unknown" and actions == []


def test_job_diferente_do_exibido_e_recusado(world):
    build, _, client = world
    db = build()
    resp = client.post("/posts/23/resolve-unknown", json={
        "source_job_id": "55555555-5555-5555-5555-555555555555", "outcome": "published", "confirmed": True})
    assert resp.status_code == 409
    assert db.tables["publish_jobs"][0]["status"] == "unknown"


@pytest.mark.parametrize("path,body", [
    ("/posts/23/resolve-unknown", {"source_job_id": SOURCE_JOB, "outcome": "published", "confirmed": True}),
    ("/posts/23/retry-failed", {"source_job_id": SOURCE_JOB, "confirmed": True}),
])
def test_outra_conta_nao_decide_nem_reenvia(world, path, body):
    build, actions, client = world
    db = build(status="failed" if "retry" in path else "unknown")
    before = [dict(row) for row in db.tables["publish_jobs"]]
    app.dependency_overrides[get_current_user_id] = lambda: OTHER
    assert client.post(path, json=body).status_code in (403, 404)
    assert db.tables["publish_jobs"] == before and actions == []


def test_post_de_campanha_usa_controles_da_campanha(world):
    build, _, client = world
    db = build(origin="campaign")
    assert _resolve(client, "published").status_code == 409
    assert db.tables["publish_jobs"][0]["status"] == "unknown"


def test_threads_mantem_link_obrigatorio_para_confirmar(world):
    build, _, client = world
    db = build(network="threads")
    assert _resolve(client, "published").status_code == 422
    link = "https://www.threads.net/@loja/post/AbC123def"
    resp = _resolve(client, "published", permalink=link)
    assert resp.status_code == 200 and resp.json()["proof_url"] == link
    assert db.tables["publish_jobs"][0]["external_id"] == link


def test_threads_nao_publicado_tambem_vira_failed(world):
    build, _, client = world
    db = build(network="threads")
    assert _resolve(client, "not_published").status_code == 200
    assert db.tables["publish_jobs"][0]["status"] == "failed"


@pytest.mark.parametrize("network,link,expected", [
    ("facebook", "https://www.facebook.com/permalink.php?story_fbid=1&id=2",
     "https://www.facebook.com/permalink.php?story_fbid=1&id=2"),
    ("instagram", "https://www.instagram.com/p/AbC123/?igsh=xyz", "https://www.instagram.com/p/AbC123/"),
    ("x", "https://x.com/loja/status/123", "https://x.com/loja/status/123"),
    ("tiktok", "https://www.tiktok.com/@loja/video/1", "https://www.tiktok.com/@loja/video/1"),
])
def test_link_opcional_validado_no_dominio_da_rede(world, network, link, expected):
    build, _, client = world
    db = build(network=network)
    resp = _resolve(client, "published", permalink=link)
    assert resp.status_code == 200
    assert db.tables["publish_jobs"][0]["external_id"] == expected


@pytest.mark.parametrize("link", [
    "http://www.facebook.com/x",
    "https://facebook.com.evil.example/x",
    "https://www.facebook.com/x?access_token=segredo",
    "https://user:pw@www.facebook.com/x",
    "javascript:alert(1)",
])
def test_link_fora_da_rede_ou_com_credencial_e_recusado(world, link):
    build, actions, client = world
    db = build(network="facebook")
    assert _resolve(client, "published", permalink=link).status_code == 422
    assert db.tables["publish_jobs"][0]["status"] == "unknown" and actions == []
