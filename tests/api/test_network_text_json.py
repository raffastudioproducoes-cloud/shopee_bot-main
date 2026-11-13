"""Regressão: posts 938/939 publicados com o JSON {"threads": "..."} como texto.

Causa: a IA devolveu o mapa com quebras de linha cruas na string; o
json.loads estrito recusava, e com uma só variante o JSON cru virava o texto.
Provedor de IA simulado; nenhuma chamada real a redes sociais.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.network_text import unwrap_network_text
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id
from api.text_variants import generate_variants

LINK = "https://s.shopee.com.br/an_redir?origin_link=x&affiliate_id=18320010033"
BODY = ("Renove seu banheiro com a Espelheira com Porta Cleo, disponível em várias cores. "
        "Garanta já o seu com segurança diretamente pela Shopee! \n\n" + LINK + " #BanheiroOrganizado")
# Exatamente o formato que foi gravado: chave única "threads", newline cru na string.
RAW_ONE_KEY = '{"threads": "' + BODY + '"}'
PRODUCT = {"name": "Armário Espelheira com Porta Cleo", "commission_link": LINK}


class FakeAI:
    def __init__(self, *answers):
        self.answers = list(answers)

    def __call__(self, _prompt, _max_tokens):
        return self.answers.pop(0)


# ── helper ──────────────────────────────────────────────────────────────────

def test_one_key_map_serves_both_networks():
    assert unwrap_network_text(RAW_ONE_KEY, "threads") == BODY.strip()
    assert unwrap_network_text(RAW_ONE_KEY, "facebook") == BODY.strip()  # rede sem chave: primeiro valor
    assert unwrap_network_text(RAW_ONE_KEY) == BODY.strip()


def test_two_key_map_picks_the_job_network():
    raw = json.dumps({"facebook": "Texto FB " + LINK, "threads": "Texto Threads " + LINK})
    assert unwrap_network_text(raw, "facebook") == "Texto FB " + LINK
    assert unwrap_network_text(raw, "threads") == "Texto Threads " + LINK


@pytest.mark.parametrize("text", [
    BODY, "", "{oi}", '{"preco": "10"}', '{"threads": 3}', "Promo {\"threads\": \"x\"} hoje",
])
def test_normal_text_is_untouched(text):
    assert unwrap_network_text(text, "threads") == text


# ── geração ─────────────────────────────────────────────────────────────────

def test_single_network_ai_json_with_raw_newlines_becomes_plain_text():
    out = generate_variants(PRODUCT, "casual", ["threads"], FakeAI(RAW_ONE_KEY))
    assert out[0]["text"].startswith("Renove seu banheiro")
    assert not out[0]["text"].lstrip().startswith("{")
    assert LINK in out[0]["text"]


def test_two_networks_ai_json_with_raw_newlines_is_parsed_per_network():
    raw = '{"facebook": "FB longo\n\n' + LINK + '", "threads": "Threads curto\n' + LINK + '"}'
    out = {v["key"]: v["text"] for v in generate_variants(PRODUCT, "casual", ["facebook", "threads"], FakeAI(raw))}
    assert out == {"facebook": "FB longo\n\n" + LINK, "threads": "Threads curto\n" + LINK}


# ── criação / exibição ──────────────────────────────────────────────────────

SCHEDULE = {"trigger": "cron", "time": "10:00", "days_of_week": [0]}


@pytest.fixture
def api(fake_db, monkeypatch):
    db = fake_db({"products": [], "posts": [], "medias": [], "posts_medias": [], "posts_products": []})
    monkeypatch.setattr(posts_module, "supabase", db)

    async def fake_job(**_kw):
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app), db
    app.dependency_overrides.clear()


def test_batch_with_one_key_map_for_two_networks_stores_clean_text(api):
    c, db = api
    res = c.post("/posts/batch", json={
        "compositions": [
            {"network": "facebook", "texts": [RAW_ONE_KEY]},
            {"network": "threads", "texts": [RAW_ONE_KEY]},
        ],
        "schedule": SCHEDULE,
    })
    assert res.status_code == 201, res.text
    assert {row["network"]: row["text"] for row in db.tables["posts"]} == {
        "facebook": BODY.strip(), "threads": BODY.strip(),
    }


def test_batch_with_two_key_map_stores_each_network_text(api):
    c, db = api
    raw = json.dumps({"facebook": "FB " + LINK, "threads": "TH " + LINK})
    res = c.post("/posts/batch", json={
        "compositions": [{"network": "facebook", "texts": [raw]}, {"network": "threads", "texts": [raw]}],
        "schedule": SCHEDULE,
    })
    assert res.status_code == 201, res.text
    assert {row["network"]: row["text"] for row in db.tables["posts"]} == {
        "facebook": "FB " + LINK, "threads": "TH " + LINK,
    }


def test_existing_json_post_is_listed_and_detailed_as_plain_text(api):
    c, db = api
    db.tables["posts"].append({
        "id": 939, "user_id": 42, "profile_id": "profile-a", "post_id": None,
        "network": "facebook", "text": RAW_ONE_KEY, "created_at": "2026-11-12T10:00:00+00:00",
    })
    detail = c.get("/posts/939")
    assert detail.status_code == 200, detail.text
    assert detail.json()["text"] == BODY.strip() and detail.json()["texts"] == [BODY.strip()]
    listing = c.get("/posts")
    assert listing.status_code == 200, listing.text
    item = next(p for p in listing.json()["data"] if p["id"] == 939)
    assert item["text"] == BODY.strip() and item["texts"] == [BODY.strip()]


# ── publicador (database/posts.get, usado por todos os bot_post_*) ──────────

@pytest.fixture
def db_posts(monkeypatch):
    root = Path(__file__).resolve().parents[2] / "database"

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    stub = types.ModuleType("shopee_bot.database")
    stub.query_db = stub.execute_db = lambda *a, **k: []
    stub.post_content_snapshot = load("_pcs_under_test", root / "post_content_snapshot.py")
    stub.post_link_redirects = types.SimpleNamespace(rewrite_parts=lambda parts, _job: parts)
    monkeypatch.setitem(sys.modules, "shopee_bot.database", stub)
    return load("_posts_under_test", root / "posts.py")


@pytest.mark.parametrize("network, stored, expected", [
    ("facebook", RAW_ONE_KEY, BODY.strip()),
    ("threads", RAW_ONE_KEY, BODY.strip()),
    ("facebook", json.dumps({"facebook": "FB", "threads": "TH"}), "FB"),
    ("threads", "Texto normal", "Texto normal"),
])
def test_publisher_never_receives_json(monkeypatch, db_posts, network, stored, expected):
    rows = [{"id": 1, "text": stored, "depth": 0, "network": network, "medias": [], "product_ids": []}]
    monkeypatch.setattr(db_posts, "query_db", lambda *_a, **_k: rows)
    assert db_posts.get(42, 1, "profile-a")[0]["text"] == expected
