"""Validação por rede no servidor (api/network_limits.py) + recusa em
POST /posts — o front bloqueia, mas o servidor não pode confiar nele."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.network_limits import GB, MB, errors_detail, text_length, validate_post, NETWORK_RULES
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id


def _errors(*args, **kw):
    return [i["message"] for i in validate_post(*args, **kw) if i["level"] == "error"]


class TestText:
    def test_threads_500_ok_501_blocked(self):
        assert _errors("threads", ["a" * 500], []) == []
        assert _errors("threads", ["a" * 501], []) == [
            "Threads: texto máx. 500 caracteres (você tem 501)"
        ]

    def test_x_counts_url_as_23_and_emoji_as_2(self):
        rule = NETWORK_RULES["x"]
        assert text_length(rule, "https://exemplo.com/um/link/bem/comprido/mesmo") == 23
        assert text_length(rule, "oi😀") == 4
        assert _errors("x", ["a" * 256 + " https://x.co/a"], []) == []  # 256 + 1 + 23 = 280
        assert _errors("x", ["a" * 257 + " https://x.co/a"], [])

    def test_thread_parts_checked_only_where_published(self):
        assert _errors("x", ["ok", "b" * 281], []) == ["X: texto máx. 280 caracteres na parte 2 (você tem 281)"]
        # A filtragem é interna: Instagram publica só a legenda, sem aviso.
        issues = validate_post("instagram", ["ok", "b" * 5000], [{"file_name": "a.jpg", "size": 1}])
        assert issues == []

    def test_tiktok_counts_utf16(self):
        assert text_length(NETWORK_RULES["tiktok"], "😀") == 2

    def test_links_hashtags_mentions(self):
        assert _errors("threads", [" ".join(f"https://a.com/{i}" for i in range(6))], [])
        assert _errors("threads", ["#um #dois"], []) == ["Threads: máx. 1 hashtag(s) (você tem 2)"]
        media = [{"file_name": "a.jpg", "size": 1}]
        assert _errors("instagram", [" ".join(f"#t{i}" for i in range(31))], media)
        assert _errors("instagram", [" ".join(f"@u{i}" for i in range(21))], media)
        assert _errors("instagram", [" ".join(f"#t{i}" for i in range(30))], media) == []

    def test_unverified_limit_is_warning(self):
        issues = validate_post("facebook", ["a" * 70000], [])
        assert [i["level"] for i in issues] == ["warn"]
        assert errors_detail(issues) is None


class TestMedia:
    def test_x_four_images_ok_five_blocked_and_no_mix(self):
        img = {"file_name": "a.png", "size": MB}
        assert _errors("x", ["oi"], [img] * 4) == []
        assert _errors("x", ["oi"], [img] * 5) == ["X: máx. 4 imagem(s) (você tem 5)"]
        assert "X: não mistura imagem, GIF e vídeo no mesmo post" in _errors(
            "x", ["oi"], [img, {"file_name": "v.mp4", "size": MB}]
        )

    def test_size_and_format(self):
        assert _errors("x", ["oi"], [{"file_name": "a.png", "size": 6 * MB}]) == ["X: a.png passa de 5 MB"]
        assert _errors("instagram", ["oi"], [{"file_name": "a.png", "size": 1}]) == [
            "Instagram: não aceita .png (a.png); use .jpeg, .jpg, .mp4"
        ]
        assert _errors("threads", ["oi"], [{"file_name": "v.mp4", "size": 2 * GB}]) == ["Threads: v.mp4 passa de 1 GB"]

    def test_mov_is_not_accepted_on_any_network(self):
        for net in NETWORK_RULES:
            issues = validate_post(net, ["oi"], [{"file_name": "v.mov", "size": MB}], check_required_media=False)
            assert any(".mov" in i["message"] and "não aceita" in i["message"] for i in issues), net

    def test_tiktok_requires_video_only_on_publish(self):
        assert _errors("tiktok", ["oi"], [], check_required_media=False) == []
        assert _errors("tiktok", ["oi"], []) == ["TikTok: exige 1 vídeo (.mp4)"]
        assert _errors("tiktok", ["oi"], [{"file_name": "a.jpg", "size": 1}], check_required_media=False)

    def test_instagram_product_photo_counts_as_media(self):
        assert _errors("instagram", ["oi"], []) == ["Instagram: exige imagem/vídeo (ou um produto com foto)"]
        assert _errors("instagram", ["oi"], [], product_count=1) == []


@pytest.fixture
def client(fake_db, monkeypatch):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    db = fake_db({"posts": [], "medias": [{"id": 5, "user_id": 42, "profile_id": "profile-a", "file_name": "a.png", "size": MB}]})
    monkeypatch.setattr(posts_module, "supabase", db)

    async def fake_job(**kw):
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    yield TestClient(app), db
    app.dependency_overrides.clear()


SCHEDULE = {"trigger": "cron", "time": "10:00", "days_of_week": [0]}


def test_create_rejects_text_over_network_limit(client):
    c, db = client
    res = c.post("/posts", json={"texts": ["a" * 281], "schedule": SCHEDULE, "network": "x"})
    assert res.status_code == 422
    assert res.json()["detail"] == "X: texto máx. 280 caracteres (você tem 281)"
    assert db.tables["posts"] == []


def test_x_is_enabled_by_default_in_production_module():
    """O conftest zera DISABLED_NETWORKS; aqui carrega o módulo cru do disco."""
    import importlib.util
    from api import network_limits

    spec = importlib.util.spec_from_file_location("network_limits_raw", network_limits.__file__)
    raw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(raw)

    assert raw.DISABLED_NETWORKS == {}
    assert raw.is_network_disabled("x") is None


def test_create_accepts_x_post(client):
    c, db = client
    res = c.post("/posts", json={"texts": ["oi"], "schedule": SCHEDULE, "network": "x"})
    assert res.status_code == 201
    assert [p["network"] for p in db.tables["posts"]] == ["x"]


def test_create_rejects_disabled_network(client, monkeypatch):
    from api import network_limits

    monkeypatch.setitem(
        network_limits.DISABLED_NETWORKS,
        "x",
        "X estará disponível em um plano pago em breve",
    )
    c, db = client

    res = c.post("/posts", json={"texts": ["oi"], "schedule": SCHEDULE, "network": "x"})

    assert res.status_code == 422
    assert res.json()["detail"] == "X estará disponível em um plano pago em breve"
    assert db.tables["posts"] == []


def test_create_reuses_media_without_reupload(client):
    c, db = client
    res = c.post("/posts", json={"texts": ["oi"], "schedule": SCHEDULE, "network": "x", "media_ids": [5]})
    assert res.status_code == 201
    links = db.tables["posts_medias"]
    assert [(l["post_id"], l["media_id"]) for l in links] == [(res.json()["id"], 5)]


def test_create_rejects_reused_media_invalid_for_network(client):
    c, db = client
    res = c.post("/posts", json={"texts": ["oi"], "schedule": SCHEDULE, "network": "instagram", "media_ids": [5]})
    assert res.status_code == 422
    assert "Instagram: não aceita .png" in res.json()["detail"]


def test_upload_rejects_format_not_accepted_by_post_network(client, monkeypatch, tmp_path):
    c, db = client
    monkeypatch.setattr(posts_module, "MEDIA_ROOT", tmp_path)
    db.tables["posts"].append({"id": 7, "user_id": 42, "profile_id": "profile-a", "text": "oi", "post_id": None, "network": "instagram"})
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (2, 2)).save(buf, format="PNG")
    png = buf.getvalue()
    db.storage = MagicMock()
    res = c.post("/posts/7/media", files={"file": ("foto.png", png, "image/png")})
    assert res.status_code == 422
    assert "Instagram: não aceita .png (foto.png)" in res.json()["detail"]
    assert list(tmp_path.iterdir()) == []
    db.storage.from_.return_value.upload.assert_not_called()


def _names(medias):
    return [m["file_name"] for m in medias]


def _m(name):
    return {"id": 1, "file_name": name, "size": 1024}


@pytest.mark.parametrize(
    "network, files, expected",
    [
        ("x", ["anim.gif", "clip.mp4"], ["anim.gif"]),  # X não entrega vídeo: fica o GIF
        ("facebook", ["clip.mp4", "foto.jpg"], ["foto.jpg"]),  # foto primeiro
        ("tiktok", ["foto.jpg", "clip.mp4"], ["clip.mp4"]),
        ("instagram", ["foto.jpg", "clip.mp4"], ["foto.jpg", "clip.mp4"]),
    ],
)
def test_adapt_media_escolhe_grupo_entre_os_modos_entregues(network, files, expected):
    from api.network_limits import adapt_media

    kept, _ = adapt_media(network, [_m(f) for f in files])
    assert _names(kept) == expected


class TestShopeeVideo:
    def test_rule_shape(self):
        rule = NETWORK_RULES["shopee_video"]
        assert rule["requires_media"] == "video" and rule["exts"] == {"mp4"}
        assert rule["max_video"] == 1 and rule["max_image"] == 0
        assert rule["max_chars"] == 150 and rule["delivered_modes"] == {"video"}
        assert rule["supports_text_only"] is False and rule["max_products"] == 6
        assert (rule["min_video_seconds"], rule["max_video_seconds"]) == (3, 60)

    def test_other_networks_default_to_one_product(self):
        from api.network_limits import max_products
        assert max_products("shopee_video") == 6
        for name in ("threads", "x", "facebook", "instagram", "tiktok"):
            assert max_products(name) == 1

    def test_caption_and_video_required(self):
        video = [{"file_name": "v.mp4", "size": 10 * MB}]
        assert _errors("shopee_video", ["a" * 150], video) == []
        assert _errors("shopee_video", ["a" * 151], video) == [
            "Shopee Vídeo: texto máx. 150 caracteres (você tem 151)"
        ]
        assert _errors("shopee_video", ["oi"], []) == ["Shopee Vídeo: exige 1 vídeo (.mp4)"]
        assert "Shopee Vídeo: não aceita imagem" in _errors(
            "shopee_video", ["oi"], video + [{"file_name": "a.jpg", "size": 1}])

    def test_product_count_over_network_limit_is_clear_error(self):
        video = [{"file_name": "v.mp4", "size": 1}]
        assert _errors("shopee_video", ["oi"], video, product_count=6) == []
        assert _errors("shopee_video", ["oi"], video, product_count=7) == [
            "Shopee Vídeo: máx. 6 produto(s) por post (você tem 7)"
        ]
        assert _errors("threads", ["oi"], [], product_count=2) == [
            "Threads: máx. 1 produto(s) por post (você tem 2)"
        ]

    def test_products_for_network_keeps_user_order(self):
        from api.network_limits import products_for_network
        ids = [30, 10, 20, 40, 50, 60, 70]
        assert products_for_network("shopee_video", ids) == [30, 10, 20, 40, 50, 60]
        assert products_for_network("threads", ids) == [30]
        assert products_for_network("tiktok", []) == []

    def test_adapt_media_keeps_single_mp4(self):
        from api.network_limits import adapt_media
        medias = [{"id": 1, "file_name": "a.jpg", "size": 1}, {"id": 2, "file_name": "v.mp4", "size": 1}]
        kept, dropped = adapt_media("shopee_video", medias)
        assert [m["id"] for m in kept] == [2] and dropped[0]["id"] == 1
