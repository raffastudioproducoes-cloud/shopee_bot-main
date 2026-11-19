"""Produtos por rede: o lote leva até 6 produtos se Shopee Vídeo estiver
selecionada; cada rede grava só os que aceita (Shopee Vídeo 6, demais 1)."""

from datetime import datetime, timedelta, timezone

from test_posts_media_drafts import _client

VIDEO_DRAFT = "55555555-5555-4555-8555-555555555555"


def _products(db, ids, user_id=42):
    db.tables["products"] = [{"id": pid, "user_id": user_id, "product_id": 9000 + pid} for pid in ids]


def _video_client(fake_db, monkeypatch):
    client, db = _client(fake_db, monkeypatch)
    db.tables["temporary_media_uploads"].append({
        "id": VIDEO_DRAFT, "user_id": 42, "profile_id": "profile-a", "status": "ready",
        "storage_bucket": "post-media", "storage_key": "drafts/42/profile-a/v.mp4",
        "file_name": "v.mp4", "size_bytes": 1000, "media_type": "VIDEO",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    })

    async def fake_job(**_kwargs):
        return "job-1"

    from api.routers import posts as posts_module
    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    return client, db


def _body(networks, product_ids):
    return {
        "compositions": [{"network": n, "texts": ["copy"]} for n in networks],
        "product_ids": product_ids,
        "draft_media_ids": [VIDEO_DRAFT],
        "schedule": {"trigger": "cron", "time": "10:00", "days_of_week": [0]},
    }


def _linked(db, network):
    post_id = next(p["id"] for p in db.tables["posts"] if p.get("network") == network)
    rows = sorted((r for r in db.tables["posts_products"] if r["post_id"] == post_id),
                  key=lambda r: r["display_order"])
    return [r["product_id"] for r in rows]


def test_batch_cuts_products_per_network(fake_db, monkeypatch):
    client, db = _video_client(fake_db, monkeypatch)
    _products(db, [3, 1, 2])

    response = client.post("/posts/batch", json=_body(["threads", "shopee_video"], [3, 1, 2]))

    assert response.status_code == 201, response.text
    assert {row["network"] for row in response.json()["created"]} == {"threads", "shopee_video"}
    assert _linked(db, "threads") == [3]
    assert _linked(db, "shopee_video") == [3, 1, 2]
    threads = next(r for r in response.json()["created"] if r["network"] == "threads")
    assert any("1 de 3 produtos" in w for w in threads["warnings"])


def test_batch_without_shopee_video_keeps_one_product_limit(fake_db, monkeypatch):
    client, db = _video_client(fake_db, monkeypatch)
    _products(db, [1, 2])

    response = client.post("/posts/batch", json=_body(["threads"], [1, 2]))

    assert response.status_code == 422
    assert response.json()["detail"] == "Selecione no máximo 1 produto por post"
    assert db.tables.get("posts", []) == []


def test_batch_rejects_more_than_six_products(fake_db, monkeypatch):
    client, db = _video_client(fake_db, monkeypatch)
    _products(db, list(range(1, 8)))

    response = client.post("/posts/batch", json=_body(["shopee_video"], list(range(1, 8))))

    assert response.status_code == 422
    assert response.json()["detail"] == "Selecione no máximo 6 produtos por post"


def test_batch_rejects_duplicate_products(fake_db, monkeypatch):
    client, db = _video_client(fake_db, monkeypatch)
    _products(db, [1])

    response = client.post("/posts/batch", json=_body(["shopee_video"], [1, 1]))

    assert response.status_code == 422
    assert "repetido" in response.json()["detail"]


def test_batch_still_rejects_products_from_other_accounts(fake_db, monkeypatch):
    client, db = _video_client(fake_db, monkeypatch)
    _products(db, [1, 2])
    db.tables["products"].append({"id": 3, "user_id": 99, "product_id": 1})

    response = client.post("/posts/batch", json=_body(["shopee_video"], [1, 2, 3]))

    assert response.status_code == 400
    assert db.tables.get("posts", []) == []


def test_preview_shows_shopee_video_mode(fake_db, monkeypatch):
    client, db = _video_client(fake_db, monkeypatch)
    _products(db, [1, 2])

    response = client.post("/posts/preview", json=_body(["shopee_video", "instagram"], [1, 2]))

    assert response.status_code == 200, response.text
    plans = {p["network"]: p for p in response.json()["plans"]}
    assert plans["shopee_video"]["mode"] == "video"
    assert plans["shopee_video"]["blocked_reason"] is None
