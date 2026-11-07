"""Regressões de insights por publicação após remover as sondas manuais.

A validação real acontece no pipeline de cache dos posts confirmados;
não há mais a rota de diagnóstico /analytics/probe.
"""

from api.post_insights import summarize_post_metrics


def _published_facebook_job(external_id="222"):
    return {"id": "job-fb", "network": "facebook", "external_id": external_id}


def test_facebook_cache_preserves_official_zero_without_account_metrics():
    metrics, collected, eligible, states = summarize_post_metrics(
        [_published_facebook_job()],
        {"job-fb": {
            "network": "facebook", "external_id": "222", "state": "ok",
            "views": 0, "likes": 0,
        }},
    )
    assert metrics["views"] == 0
    assert metrics["likes"] == 0
    assert metrics["comments"] is None
    assert (collected, eligible, states) == (1, 1, {"ok"})


def test_facebook_without_published_posts_never_invents_zero():
    metrics, collected, eligible, states = summarize_post_metrics([], {})
    assert all(value is None for value in metrics.values())
    assert (collected, eligible, states) == (0, 0, set())


def test_facebook_rejects_insights_with_other_post_identity():
    metrics, collected, eligible, states = summarize_post_metrics(
        [_published_facebook_job()],
        {"job-fb": {
            "network": "facebook", "external_id": "other-post",
            "state": "ok", "views": 99999,
        }},
    )
    assert metrics["views"] is None
    assert (collected, eligible, states) == (0, 1, {"not_collected"})


def test_facebook_permission_failure_does_not_leak_token_or_fake_metrics():
    metrics, collected, eligible, states = summarize_post_metrics(
        [_published_facebook_job()],
        {"job-fb": {
            "network": "facebook", "external_id": "222",
            "state": "permission_required", "views": None,
            "access_token": "private-page-token",
        }},
    )
    assert metrics["views"] is None
    assert "private-page-token" not in str(metrics)
    assert (collected, eligible, states) == (0, 1, {"permission_required"})
