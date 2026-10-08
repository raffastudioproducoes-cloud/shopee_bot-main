"""Conjunto mínimo de textos por limite das redes (api/text_variants.py),
geração com refação única por variante e group_id na criação multi-rede.
Provedor de IA simulado: nenhuma chamada real."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.network_limits import NETWORK_RULES, text_length
from api.routers import posts as posts_module
from api.routers.auth import get_current_user_id
from api.text_variants import PRACTICAL_MAX_CHARS, generate_variants, plan_variants, variant_issues
from apis.llm import LLMError

LINK = "https://s.shopee.com.br/" + "a" * 60  # 84 caracteres; no X conta 23
FENCE = "\x60\x60\x60"


def _plan(nets):
    return [(v["max_chars"], v["networks"]) for v in plan_variants(nets)]


# ── agrupamento ───────────────────────────────────────────────────────────────

def test_x_facebook_instagram_gives_long_shared_and_short_x():
    assert _plan(["x", "facebook", "instagram"]) == [(2200, ["facebook", "instagram"]), (280, ["x"])]


def test_threads_and_x_are_two_ranges():
    assert _plan(["x", "threads"]) == [(500, ["threads"]), (280, ["x"])]


def test_all_networks_three_ranges():
    assert _plan(list(NETWORK_RULES)) == [
        (2200, ["facebook", "instagram", "tiktok"]), (500, ["threads"]), (280, ["x"]),
    ]


def test_single_network_and_same_limit_have_one_text():
    assert _plan(["facebook"]) == [(PRACTICAL_MAX_CHARS, ["facebook"])]
    assert _plan(["instagram", "tiktok", "facebook"]) == [(2200, ["facebook", "instagram", "tiktok"])]
    assert _plan(["x", "x"]) == [(280, ["x"])]
    assert _plan([]) == [(PRACTICAL_MAX_CHARS, [])]


def test_x_counting_link_23_and_emoji_2():
    x = plan_variants(["x"])[0]
    text = "\U0001F525" * 100 + " " + LINK + " " + "a" * 34  # 200 + 1 + 23 + 1 + 34 = 259
    assert text_length(NETWORK_RULES["x"], text) == 259
    assert variant_issues(x, text) == []
    assert variant_issues(x, text + "a" * 22) == ["X: texto máx. 280 caracteres (você tem 281)"]
    # 300 caracteres reais, mas o link conta 23: cabe no X
    assert len("b" * 216 + LINK) == 300 and variant_issues(x, "b" * 216 + LINK) == []


def test_group_applies_text_rules_of_its_networks():
    threads = plan_variants(["threads"])[0]
    assert variant_issues(threads, "oi #um #dois") == ["Threads: máx. 1 hashtag(s) (você tem 2)"]
    facebook = plan_variants(["facebook"])[0]
    assert variant_issues(facebook, "a" * 2201) == ["texto máx. 2200 caracteres (você tem 2201)"]


# ── geração (provedor simulado) ──────────────────────────────────────────────

PRODUCT = {"name": "Fone", "commission": 10, "price_min": 10, "price_max": 20, "commission_link": LINK}


class FakeAI:
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        return self.answers.pop(0)


def test_one_call_for_all_variants_with_limits_in_prompt():
    ai = FakeAI(json.dumps({"2200": "longo " + LINK, "280": "curto " + LINK}))
    out = generate_variants(PRODUCT, "casual", ["x", "facebook", "instagram"], ai)

    assert len(ai.prompts) == 1
    assert "no máximo 2200 caracteres" in ai.prompts[0] and "no máximo 280 caracteres" in ai.prompts[0]
    assert "cada link conta 23" in ai.prompts[0] and LINK in ai.prompts[0]
    assert [(v["networks"], v["text"], v["over_limit"]) for v in out] == [
        (["facebook", "instagram"], "longo " + LINK, False), (["x"], "curto " + LINK, False),
    ]


def test_over_limit_variant_is_redone_once_alone():
    ai = FakeAI(
        FENCE + "json\n" + json.dumps({"2200": "longo", "280": "x" * 300}) + "\n" + FENCE,
        json.dumps({"280": "curtinho"}),
    )
    out = generate_variants(PRODUCT, "casual", ["x", "facebook"], ai)

    assert len(ai.prompts) == 2 and "MAIS CURTO" in ai.prompts[1]
    assert json.dumps("2200") not in ai.prompts[1]  # só a variante que passou
    assert [v["text"] for v in out] == ["longo", "curtinho"]
    assert not any(v["over_limit"] for v in out)


def test_still_over_after_retry_returns_with_warning_untruncated():
    ai = FakeAI(json.dumps({"280": "x" * 300}), json.dumps({"280": "y" * 290}))
    (out,) = generate_variants(PRODUCT, "casual", ["x"], ai)

    assert len(ai.prompts) == 2  # refaz UMA vez só
    assert out["text"] == "y" * 290 and out["over_limit"] is True
    assert out["issues"] == ["X: texto máx. 280 caracteres (você tem 290)"]


def test_bad_json_with_many_variants_is_clear_error():
    with pytest.raises(LLMError) as exc:
        generate_variants(PRODUCT, "casual", ["x", "facebook"], FakeAI("só texto"))
    assert exc.value.kind == "bad_response"


# ── endpoints ────────────────────────────────────────────────────────────────

@pytest.fixture
def api(fake_db, monkeypatch):
    db = fake_db({
        "products": [{**PRODUCT, "id": 1, "user_id": 42}, {**PRODUCT, "id": 2, "user_id": 99}],
        "posts": [], "medias": [], "posts_medias": [], "posts_products": [],
    })
    monkeypatch.setattr(posts_module, "supabase", db)
    from api.routers import credentials
    monkeypatch.setattr(credentials, "resolve_ai_key", lambda *_a, **_k: ("gemini", "k", None))

    async def fake_job(**_kw):
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    app.dependency_overrides[get_current_user_id] = lambda: 42
    yield TestClient(app), db, monkeypatch
    app.dependency_overrides.clear()


def _fake_llm(monkeypatch, answer):
    import apis.llm
    monkeypatch.setattr(apis.llm, "complete", lambda *_a, **_k: answer)


def test_generate_copy_returns_variants_and_legacy_text(api):
    c, _db, mp = api
    _fake_llm(mp, json.dumps({"2200": "longo", "280": "curto"}))
    res = c.post("/posts/generate-copy", json={"product_id": 1, "networks": ["x", "facebook", "instagram"]})

    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "longo"
    assert [(v["key"], v["max_chars"], v["networks"], v["text"]) for v in body["variants"]] == [
        ("2200", 2200, ["facebook", "instagram"], "longo"), ("280", 280, ["x"], "curto"),
    ]


def test_generate_copy_without_networks_keeps_single_text(api):
    c, _db, mp = api
    _fake_llm(mp, "Texto IA")
    body = c.post("/posts/generate-copy", json={"product_id": 1}).json()
    assert body["text"] == "Texto IA" and len(body["variants"]) == 1


def test_generate_copy_is_scoped_to_owner_and_validates_networks(api):
    c, _db, mp = api
    _fake_llm(mp, "Texto IA")
    assert c.post("/posts/generate-copy", json={"product_id": 2}).status_code == 404
    assert c.post("/posts/generate-copy", json={"product_id": 1, "networks": ["myspace"]}).status_code == 422


SCHEDULE = {"trigger": "date", "run_date": "2030-01-01T10:00:00"}
GROUP = "6f1c1f3e-2b7a-4c39-9a8e-0c7d2f5b1a11"


def test_create_stores_valid_group_id_on_head(api):
    c, db, _mp = api
    for net, text in (("facebook", "longo " * 60), ("x", "curto")):
        res = c.post("/posts", json={"texts": [text], "schedule": SCHEDULE, "network": net, "group_id": GROUP})
        assert res.status_code == 201 and res.json()["group_id"] == GROUP
    assert [(p["network"], p["group_id"], p["text"][:5]) for p in db.tables["posts"]] == [
        ("facebook", GROUP, "longo"), ("x", GROUP, "curto"),
    ]


def test_create_rejects_invalid_group_id_without_writing(api):
    c, db, _mp = api
    res = c.post("/posts", json={"texts": ["oi"], "schedule": SCHEDULE, "network": "x", "group_id": "nao-e-uuid"})
    assert res.status_code == 422 and db.tables["posts"] == []


def test_create_without_group_id_omits_column(api):
    c, db, _mp = api
    assert c.post("/posts", json={"texts": ["oi"], "schedule": SCHEDULE}).status_code == 201
    assert "group_id" not in db.tables["posts"][0]


def test_each_network_post_still_validated_against_its_own_limit(api):
    c, db, _mp = api
    res = c.post("/posts", json={"texts": ["a" * 600], "schedule": SCHEDULE, "network": "x", "group_id": GROUP})
    assert res.status_code == 422 and res.json()["detail"] == "X: texto máx. 280 caracteres (você tem 600)"
    assert db.tables["posts"] == []


def test_group_id_migration_is_additive_and_idempotent():
    sql = (Path(__file__).resolve().parents[2] / "database" / "migrations"
           / "044_add_group_id_to_posts.sql").read_text(encoding="utf-8")
    statements = "\n".join(line for line in sql.lower().splitlines() if not line.startswith("--"))
    assert "add column if not exists group_id uuid;" in statements
    assert "create index if not exists" in statements
    assert "drop " not in statements and "default" not in statements and "not null" not in statements
