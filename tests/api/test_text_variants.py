"""Descrições individuais por rede (api/text_variants.py),
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
from api.routers.profiles import get_current_profile_id
from api.text_variants import (
    MAX_THREAD_PARTS, PRACTICAL_MAX_CHARS, generate_variants,
    generate_thread_replies, plan_variants, variant_issues,
)
from apis.llm import LLMError

LINK = "https://s.shopee.com.br/" + "a" * 60  # 84 caracteres; no X conta 23
FENCE = "\x60\x60\x60"


def _plan(nets):
    return [(v["max_chars"], v["networks"]) for v in plan_variants(nets)]


# ── uma descrição por rede ──────────────────────────────────────────────────

def test_each_network_gets_own_variant_even_with_same_limit():
    assert _plan(["x", "facebook", "instagram"]) == [
        (2200, ["facebook"]), (2200, ["instagram"]), (280, ["x"]),
    ]


def test_threads_and_x_are_separate():
    assert _plan(["x", "threads"]) == [(500, ["threads"]), (280, ["x"])]


def test_all_networks_individual_versions():
    assert _plan(list(NETWORK_RULES)) == [
        (2200, ["facebook"]), (2200, ["instagram"]), (2200, ["tiktok"]),
        (500, ["threads"]), (280, ["x"]),
    ]


def test_single_network_and_duplicates():
    assert _plan(["facebook"]) == [(PRACTICAL_MAX_CHARS, ["facebook"])]
    assert _plan(["instagram", "tiktok", "facebook"]) == [
        (2200, ["facebook"]), (2200, ["instagram"]), (2200, ["tiktok"]),
    ]
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


def test_one_call_generates_individual_versions_with_limits_in_prompt():
    ai = FakeAI(json.dumps({
        "facebook": "Explicação " + LINK,
        "instagram": "Legenda visual " + LINK,
        "x": "Chamada breve " + LINK,
    }))
    out = generate_variants(PRODUCT, "casual", ["x", "facebook", "instagram"], ai)

    assert len(ai.prompts) == 1
    assert "no máximo 2200 caracteres" in ai.prompts[0]
    assert "no máximo 280 caracteres" in ai.prompts[0]
    assert "cada link conta 23" in ai.prompts[0] and LINK in ai.prompts[0]
    assert [(v["networks"], v["text"], v["over_limit"]) for v in out] == [
        (["facebook"], "Explicação " + LINK, False),
        (["instagram"], "Legenda visual " + LINK, False),
        (["x"], "Chamada breve " + LINK, False),
    ]
    assert not any(v["adjusted"] for v in out)


def test_over_limit_variant_is_redone_once_alone():
    ai = FakeAI(
        FENCE + "json\n" + json.dumps({
            "facebook": "longo " + LINK, "x": "x" * 300,
        }) + "\n" + FENCE,
        json.dumps({"x": "curtinho " + LINK}),
    )
    out = generate_variants(PRODUCT, "casual", ["x", "facebook"], ai)

    assert len(ai.prompts) == 2 and "MAIS CURTO" in ai.prompts[1]
    assert json.dumps("facebook") not in ai.prompts[1]
    assert [v["text"] for v in out] == ["longo " + LINK, "curtinho " + LINK]
    assert not any(v["adjusted"] for v in out)


def test_still_over_after_retry_gets_safe_validated_version_with_link():
    ai = FakeAI(json.dumps({"x": "x" * 300}), json.dumps({"x": "y" * 290}))
    (out,) = generate_variants(PRODUCT, "casual", ["x"], ai)

    assert len(ai.prompts) == 2
    assert LINK in out["text"]
    assert variant_issues(out, out["text"]) == []
    assert out["over_limit"] is False and out["adjusted"] is True


def test_threads_1208_characters_and_six_hashtags_is_adapted():
    bad = "Organize sua casa. " + "A" * 1050 + " #a #b #c #d #e #f " + LINK
    ai = FakeAI(json.dumps({"threads": bad}), json.dumps({"threads": bad}))
    (out,) = generate_variants(PRODUCT, "casual", ["threads"], ai)

    assert len(ai.prompts) == 2
    assert variant_issues(out, out["text"]) == []
    assert LINK in out["text"]
    assert out["text"].count("#") <= 1
    assert len(out["text"]) <= 500
    assert out["adjusted"] and not out["over_limit"]


def test_missing_product_link_is_restored_with_revalidation():
    ai = FakeAI(json.dumps({"threads": "Conheça o produto #casa"}))
    (out,) = generate_variants(PRODUCT, "casual", ["threads"], ai)
    assert len(ai.prompts) == 1
    assert LINK in out["text"] and out["adjusted"]
    assert not variant_issues(out, out["text"])


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
    from api.routers import auth
    monkeypatch.setattr(auth, "_login_attempts", {})
    from api.routers import credentials
    monkeypatch.setattr(credentials, "resolve_ai_key", lambda *_a, **_k: ("gemini", "k", None))

    async def fake_job(**_kw):
        return "job-1"

    monkeypatch.setattr(posts_module, "create_scheduler_job", fake_job)
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    yield TestClient(app), db, monkeypatch
    app.dependency_overrides.clear()


def _fake_llm(monkeypatch, answer):
    import apis.llm
    monkeypatch.setattr(apis.llm, "complete", lambda *_a, **_k: answer)


def test_generate_copy_returns_individual_variants_and_legacy_text(api):
    c, _db, mp = api
    _fake_llm(mp, json.dumps({
        "facebook": "Facebook " + LINK,
        "instagram": "Instagram " + LINK,
        "x": "X " + LINK,
    }))
    res = c.post("/posts/generate-copy", json={"product_id": 1, "networks": ["x", "facebook", "instagram"]})

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["text"] == "Facebook " + LINK
    assert [(v["key"], v["max_chars"], v["networks"], v["text"]) for v in body["variants"]] == [
        ("facebook", 2200, ["facebook"], "Facebook " + LINK),
        ("instagram", 2200, ["instagram"], "Instagram " + LINK),
        ("x", 280, ["x"], "X " + LINK),
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


SCHEDULE = {"trigger": "cron", "time": "10:00", "days_of_week": [0]}
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



# ── geração de todas as partes da thread ─────────────────────────────────────

def test_generate_replies_one_request_and_respects_thread_limits():
    ai = FakeAI(json.dumps({"parts": ["Primeira dica", "Segunda dica"]}))
    parts = generate_thread_replies(PRODUCT, "divertido", ["threads", "facebook"], ["Cabeçalho"], 2, ai)

    assert parts == ["Primeira dica", "Segunda dica"]
    assert len(ai.prompts) == 1
    assert "EXATAMENTE 2" in ai.prompts[0]
    assert "500 caracteres" in ai.prompts[0]


def test_generate_replies_retries_oversize_and_rejects_if_still_invalid():
    bad = json.dumps({"parts": ["x" * 501]})
    fixed = json.dumps({"parts": ["Curta e válida"]})
    ai = FakeAI(bad, fixed)
    assert generate_thread_replies(PRODUCT, "casual", ["threads"], ["Início"], 1, ai) == ["Curta e válida"]
    assert len(ai.prompts) == 2

    with pytest.raises(LLMError):
        generate_thread_replies(PRODUCT, "casual", ["threads"], ["Início"], 1, FakeAI(bad, bad))


def test_generate_replies_rejects_wrong_length_and_too_many_parts():
    with pytest.raises(LLMError):
        generate_thread_replies(PRODUCT, "casual", [], ["Início"], 2, FakeAI('{"parts":["a"]}', '{"parts":["a"]}'))
    with pytest.raises(ValueError):
        generate_thread_replies(PRODUCT, "casual", [], ["Início"], MAX_THREAD_PARTS, FakeAI())


def test_generate_copy_populates_all_open_parts(api):
    c, _db, mp = api
    answers = iter([
        json.dumps({"facebook": "Post Facebook " + LINK, "threads": "Post Threads " + LINK}),
        json.dumps({"parts": ["Dica dois", "Dica três"]}),
    ])
    import apis.llm
    mp.setattr(apis.llm, "complete", lambda *_a, **_k: next(answers))
    res = c.post("/posts/generate-copy", json={
        "product_id": 1, "networks": ["facebook", "threads"], "part_count": 3,
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["text"] == "Post Facebook " + LINK
    assert body["parts"] == ["Post Facebook " + LINK, "Dica dois", "Dica três"]
    assert body["start_index"] == 0
    assert [(v["key"], v["text"]) for v in body["variants"]] == [
        ("facebook", "Post Facebook " + LINK), ("threads", "Post Threads " + LINK),
    ]


def test_generate_copy_append_only_new_parts_without_rewriting_previous(api):
    c, _db, mp = api
    import apis.llm
    prompts = []
    def completion(_provider, _key, _model, prompt, _tokens):
        prompts.append(prompt)
        return json.dumps({"parts": ["Parte 3", "Parte 4"]})
    mp.setattr(apis.llm, "complete", completion)
    res = c.post("/posts/generate-copy", json={
        "product_id": 1, "networks": ["threads"], "part_count": 4,
        "mode": "append", "existing_texts": ["Minha descrição", "Parte 2 manual"],
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["parts"] == ["Parte 3", "Parte 4"]
    assert body["start_index"] == 2
    assert body["variants"] == []
    assert len(prompts) == 1 and "Parte 2 manual" in prompts[0]


def test_generate_copy_caps_parts_and_rejects_empty_append_context(api):
    c, _db, _mp = api
    assert c.post("/posts/generate-copy", json={"product_id": 1, "part_count": 11}).status_code == 422
    assert c.post("/posts/generate-copy", json={
        "product_id": 1, "part_count": 2, "mode": "append", "existing_texts": [],
    }).status_code == 422
    assert c.post("/posts/generate-copy", json={
        "product_id": 1, "part_count": 2, "mode": "append", "existing_texts": ["", "a"],
    }).status_code == 422


def test_server_stores_only_first_part_for_non_thread_network(api):
    c, db, _mp = api
    res = c.post("/posts", json={
        "texts": ["Legenda", "Parte que não deve ir ao Facebook"],
        "schedule": SCHEDULE, "network": "facebook",
    })
    assert res.status_code == 201, res.text
    assert [row["text"] for row in db.tables["posts"]] == ["Legenda"]


def test_server_rejects_more_than_ten_parts(api):
    c, db, _mp = api
    res = c.post("/posts", json={
        "texts": [f"Parte {i}" for i in range(MAX_THREAD_PARTS + 1)],
        "schedule": SCHEDULE, "network": "threads",
    })
    assert res.status_code == 422
    assert db.tables["posts"] == []


def test_preview_batch_filters_threads_per_network_on_server(api):
    c, _db, _mp = api
    texts = ["Legenda", "Resposta 2", "Resposta 3"]
    res = c.post("/posts/preview", json={
        "compositions": [
            {"network": "threads", "texts": texts},
            {"network": "facebook", "texts": texts},
            {"network": "instagram", "texts": texts},
            {"network": "tiktok", "texts": texts},
        ],
        "schedule": SCHEDULE,
    })
    assert res.status_code == 200, res.text
    plans = {p["network"]: p for p in res.json()["plans"]}
    assert plans["threads"]["texts"] == texts
    for network in ("facebook", "instagram", "tiktok"):
        assert plans[network]["texts"] == ["Legenda"]
        assert not any("thread" in w.lower() for w in plans[network]["warnings"])


def test_batch_persists_replies_only_for_supported_network(api):
    c, db, _mp = api
    texts = ["Legenda", "Passo dois", "Passo três"]
    res = c.post("/posts/batch", json={
        "compositions": [
            {"network": "facebook", "texts": texts},
            {"network": "threads", "texts": texts},
        ],
        "schedule": SCHEDULE,
    })
    assert res.status_code == 201, res.text
    assert {item["network"] for item in res.json()["created"]} == {"facebook", "threads"}
    rows = db.tables["posts"]
    assert len(rows) == 4  # Facebook: 1, Threads: 3
    assert len([row for row in rows if row.get("network") == "facebook"]) == 1
    thread_head = next(row for row in rows if row.get("network") == "threads")
    first_reply = next(row for row in rows if row.get("post_id") == thread_head["id"])
    assert first_reply["text"] == "Passo dois"
    assert any(row.get("post_id") == first_reply["id"] and row["text"] == "Passo três" for row in rows)
