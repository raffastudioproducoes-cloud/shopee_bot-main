"""Regra da Shopee: a palavra/logo "Shopee" não sai em texto publicado.

Filtro determinístico (api/brand_filter.py), restrição nos prompts de IA e
aplicação nos pontos de geração e de montagem do texto de publicação.
Sem rede, sem banco: IA simulada e query_db substituído.
"""
import json

import pytest

from api.brand_filter import BRAND_RULE, mentions_brand, strip_brand
from api.text_variants import (
    build_prompt, generate_short_product_description, generate_thread_replies,
    generate_variants, plan_variants, _shorten_prompt,
)
from apis import llm

AFFILIATE = "https://s.shopee.com.br/AbCd123"
PRODUCT = {"name": "Capa Shopee Xiaomi", "commission": 5, "price_min": 10,
           "price_max": 20, "commission_link": AFFILIATE}


@pytest.mark.parametrize("text, expected", [
    ("Compre na Shopee hoje", "Compre na loja hoje"),
    ("Compre na SHOPEE hoje", "Compre na loja hoje"),
    ("compre na shopee", "compre na loja"),
    ("Compre na Shopée", "Compre na loja"),
    ("Shopee tem oferta", "Loja tem oferta"),
    ("Veja. Shopee tem oferta", "Veja. Loja tem oferta"),
    ("Assista no Shopee Vídeo agora", "Assista no loja agora"),
    ("Assista no shopee video agora", "Assista no loja agora"),
    ("Oferta boa #shopee #promo", "Oferta boa #promo"),
    ("Oferta boa #Shopee", "Oferta boa"),
    ("#ShopeeBrasil oferta", "oferta"),
    ("Oferta #achadinhos #shopee\n#promo", "Oferta #achadinhos\n#promo"),
    ("sem  marca  aqui", "sem  marca  aqui"),
])
def test_strip_brand_variations(text, expected):
    assert strip_brand(text) == expected


@pytest.mark.parametrize("url", [
    "https://s.shopee.com.br/AbCd123",
    "https://shopee.com.br/produto-i.1.2",
    "https://shope.ee/abc",
    "http://shopee.com/x",
    "www.shopee.com.br/x",
    "shope.ee/abc",
    "shopee.com.br/produto",
])
def test_strip_brand_keeps_links(url):
    text = f"Compre na Shopee: {url} #shopee"
    out = strip_brand(text)
    assert url in out
    assert out == f"Compre na loja: {url}"


def test_strip_brand_no_double_space_and_idempotent():
    out = strip_brand("Oferta  na Shopee  imperdível #shopee  #promo")
    assert "  " not in out
    assert not mentions_brand(out)
    assert strip_brand(out) == out


def test_strip_brand_never_longer():
    for text in ("Shopee", "Shopee Vídeo", "na Shopee!", "#shopee"):
        assert len(strip_brand(text)) <= len(text)


def test_strip_brand_untouched_without_word():
    text = "Fone bom é barato!  \n  Link: " + AFFILIATE
    assert strip_brand(text) == text
    assert strip_brand(None) is None
    assert not mentions_brand(AFFILIATE)


def test_mentions_brand():
    assert mentions_brand("na shopee")
    assert mentions_brand("#shopee")
    assert not mentions_brand("https://shopee.com.br/x")


# ── prompts ────────────────────────────────────────────────────────────────

def _assert_rule(prompt):
    assert BRAND_RULE in prompt
    assert "afiliados Shopee" not in prompt and "afiliados da Shopee" not in prompt


def test_prompts_carry_restriction():
    variants = plan_variants(["threads", "x"])
    _assert_rule(llm._build_prompt(PRODUCT, "casual"))
    _assert_rule(build_prompt(PRODUCT, "casual", variants))
    texts = {v["key"]: "t" for v in variants}
    _assert_rule(_shorten_prompt(variants, texts, {v["key"]: ["x"] for v in variants}))

    captured = []

    def complete(prompt, _max):
        captured.append(prompt)
        return json.dumps({"parts": ["a", "b"]})

    generate_thread_replies(PRODUCT, "casual", ["threads"], ["inicio"], 2, complete)
    _assert_rule(captured[0])

    generate_short_product_description(PRODUCT, "casual", lambda p, m: (captured.append(p), "Capa boa")[1])
    _assert_rule(captured[1])


# ── geração: texto da IA nunca fica com a marca ────────────────────────────

def test_generate_variants_strips_brand_from_fallback_name():
    def complete(_prompt, _max):
        return json.dumps({"threads": "x" * 600})  # estoura e força o fallback

    out = generate_variants({**PRODUCT, "name": "Shopee"}, "casual", ["threads"], complete)
    assert not mentions_brand(out[0]["text"])
    assert AFFILIATE in out[0]["text"]


def test_short_description_filtered():
    text = generate_short_product_description(
        PRODUCT, "casual", lambda p, m: "Capa resistente, achei na Shopee #shopee")
    assert not mentions_brand(text)
    assert text.startswith("Capa resistente")


def test_generate_product_copy_filtered(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a, **k: "Oferta na Shopee!")
    assert llm.generate_product_copy(PRODUCT, "casual", "gemini", "k") == "Oferta na loja!"


# ── montagem do texto de publicação ────────────────────────────────────────

def test_publish_parts_filtered(monkeypatch):
    from database import posts as db_posts

    rows = [{"id": 1, "text": f"Achei na Shopee #shopee {AFFILIATE}", "network": "threads",
             "depth": 0, "medias": [], "product_ids": []}]
    monkeypatch.setattr(db_posts, "query_db", lambda *a, **k: rows)
    monkeypatch.setattr(db_posts.post_content_snapshot, "get", lambda: None)
    monkeypatch.setattr(db_posts.post_link_redirects, "rewrite_parts", lambda parts, _j: parts)
    out = db_posts.get(1, 1, None)
    assert out[0]["text"] == f"Achei na loja {AFFILIATE}"


def test_publish_parts_without_brand_unchanged(monkeypatch):
    from database import posts as db_posts

    original = f"Fone bom!  Veja {AFFILIATE}"
    rows = [{"id": 1, "text": original, "network": "x", "depth": 0}]
    monkeypatch.setattr(db_posts, "query_db", lambda *a, **k: rows)
    monkeypatch.setattr(db_posts.post_content_snapshot, "get", lambda: None)
    monkeypatch.setattr(db_posts.post_link_redirects, "rewrite_parts", lambda parts, _j: parts)
    assert db_posts.get(1, 1, None)[0]["text"] == original
