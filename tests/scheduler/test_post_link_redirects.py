"""Redirecionador no envio: troca só links Shopee, reaproveita token e nunca bloqueia a publicação."""
import pytest

from shopee_bot.database import post_link_redirects as redirects
from shopee_bot.database import posts
from shopee_bot.scheduler import publication_context

JOB = {"id": "job-1", "user_id": "u", "profile_id": "p", "post_id": 7, "network": "threads"}


@pytest.fixture
def fake_db(monkeypatch):
    tokens, calls = {}, []

    def query_db(sql, args=(), one=False):
        calls.append(sql)
        if "FROM publish_jobs" in sql:
            return dict(JOB)
        target = args[6]
        tokens.setdefault((args[4], target), args[0])
        return {"token": tokens[(args[4], target)]}
    monkeypatch.setattr(redirects, "query_db", query_db)
    monkeypatch.setenv("CLICK_REDIRECT_BASE_URL", "https://autoorbital.example")
    return tokens, calls


def test_replaces_only_shopee_links_and_reuses_token(fake_db):
    tokens, _ = fake_db
    parts = [{"text": "Compre: https://s.shopee.com.br/AbC1. Veja https://outro.site/x"},
             {"text": "De novo https://s.shopee.com.br/AbC1"}]
    result = redirects.rewrite_parts(parts, "job-1")
    token = tokens[("job-1", "https://s.shopee.com.br/AbC1")]
    assert len(token) >= 22
    assert result[0]["text"] == f"Compre: https://autoorbital.example/r/{token}. Veja https://outro.site/x"
    assert result[1]["text"] == f"De novo https://autoorbital.example/r/{token}"
    assert parts[0]["text"].startswith("Compre: https://s.shopee.com.br")  # original intacto
    assert len(tokens) == 1


def test_disabled_without_base_url_or_active_job(fake_db, monkeypatch):
    _, calls = fake_db
    parts = [{"text": "https://s.shopee.com.br/AbC1"}]
    assert redirects.rewrite_parts(parts, None) is parts
    monkeypatch.setenv("CLICK_REDIRECT_BASE_URL", "http://inseguro.example")
    assert redirects.rewrite_parts(parts, "job-1") is parts
    assert calls == []


def test_database_failure_keeps_direct_link(monkeypatch):
    monkeypatch.setenv("CLICK_REDIRECT_BASE_URL", "https://autoorbital.example")

    def broken(*a, **k):
        raise RuntimeError("relation post_link_clicks does not exist")
    monkeypatch.setattr(redirects, "query_db", broken)
    parts = [{"text": "https://s.shopee.com.br/AbC1"}]
    assert redirects.rewrite_parts(parts, "job-1") == parts


def test_text_over_network_limit_keeps_direct_link(fake_db):
    text = "x" * 470 + " https://s.shopee.com.br/AbC1"  # 499 chars, cabe no Threads (500)
    assert redirects.rewrite_parts([{"text": text}], "job-1")[0]["text"] == text


def test_posts_get_rewrites_only_inside_active_publication(fake_db, monkeypatch):
    monkeypatch.setattr(posts, "query_db", lambda *a, **k: [{"text": "https://s.shopee.com.br/AbC1", "medias": [], "product_ids": []}])
    assert posts.get("u", 7, "p")[0]["text"] == "https://s.shopee.com.br/AbC1"
    tokens = publication_context.activate("job-1", "claim")
    try:
        assert "/r/" in posts.get("u", 7, "p")[0]["text"]
    finally:
        publication_context.reset(tokens)
