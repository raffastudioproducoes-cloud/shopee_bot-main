"""Fase 2: coletores por post do Instagram e do Facebook com Graph API simulada.

Cobre sucesso, escopo ausente, token expirado, post removido, rate limit e a garantia
de que falha de uma rede/conta nunca derruba a coleta das outras nem vaza o token.
"""
import asyncio

import httpx
import pytest

from api import meta_post_insights as meta
from api import post_insights

TOKEN = "secret-meta-token"


def _error(code, subcode=None, status=400, message="(#10) Requires read_insights permission"):
    body = {"error": {"message": f"{message} contém {TOKEN}", "code": code, "type": "OAuthException"}}
    if subcode is not None:
        body["error"]["error_subcode"] = subcode
    return httpx.Response(status, json=body)


def _read(reader, external_id, handler):
    requests = []

    def wrapped(request):
        requests.append(request)
        return handler(request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(wrapped)) as client:
            return await reader(client, external_id, TOKEN)
    return asyncio.run(run()), requests


IG_OK = {"data": [
    {"name": "views", "period": "lifetime", "values": [{"value": 120}]},
    {"name": "reach", "period": "lifetime", "values": [{"value": 90}]},
    {"name": "likes", "period": "lifetime", "values": [{"value": 0}]},
    {"name": "comments", "period": "lifetime", "values": [{"value": 4}]},
    {"name": "saved", "period": "lifetime", "values": [{"value": 2}]},
]}


def test_instagram_success_maps_metrics_and_keeps_missing_as_none():
    (state, metrics, _), requests = _read(meta.read_instagram_media, "17890000000000001",
                                          lambda r: httpx.Response(200, json=IG_OK))
    assert state == "ok"
    assert metrics == {"views": 120, "reach": 90, "likes": 0, "comments": 4, "shares": None, "saves": 2}
    url = str(requests[0].url)
    assert requests[0].url.path == "/v26.0/17890000000000001/insights"
    assert "impressions" not in url and "plays" not in url and TOKEN not in url
    assert requests[0].headers["Authorization"] == f"Bearer {TOKEN}"


def test_instagram_unknown_metric_falls_back_once():
    answers = iter([_error(100), httpx.Response(200, json=IG_OK)])
    (state, metrics, _), requests = _read(meta.read_instagram_media, "1789", lambda r: next(answers))
    assert state == "ok" and len(requests) == 2
    assert requests[1].url.params["metric"] == ",".join(meta.IG_FALLBACK)


@pytest.mark.parametrize("response,expected", [
    (_error(10, status=403), "permission_required"),
    (_error(200), "permission_required"),
    (_error(10, status=403, message="(#10) Not enough viewers"), "access_denied"),
    (httpx.Response(403, json={}), "access_denied"),
    (_error(190, status=401), "token_expired"),
    (_error(100, 33), "not_found"),
    (_error(4), "rate_limited"),
    (_error(32), "rate_limited"),
    (_error(80001), "rate_limited"),
    (httpx.Response(500, json={}), "api_error"),
])
def test_instagram_errors_are_classified_without_raw_message(response, expected):
    (state, metrics, extra), requests = _read(meta.read_instagram_media, "1789", lambda r: response)
    assert state == expected and metrics is None and extra == {}
    assert len(requests) == 1  # nenhum retry


def test_instagram_invalid_id_never_reaches_api():
    (state, _, _), requests = _read(meta.read_instagram_media, "../me", lambda r: httpx.Response(200))
    assert state == "invalid_id" and not requests


def _facebook_handler(story="111_222", shares=True):
    def handler(request):
        path = request.url.path
        if path.endswith("/333") and request.url.params.get("fields") == "page_story_id":
            return httpx.Response(200, json={"id": "333", "page_story_id": story} if story else {"id": "333"})
        if path.endswith("/444"):
            return _error(100)  # vídeo: campo page_story_id inexistente
        if path.endswith("/111_222/insights"):
            return httpx.Response(200, json={"data": [
                {"name": "post_media_view", "period": "lifetime", "values": [{"value": 500}]},
                {"name": "post_total_media_view_unique", "period": "lifetime", "values": [{"value": 300}]},
                {"name": "post_reactions_by_type_total", "period": "lifetime",
                 "values": [{"value": {"like": 7, "love": 3}}]},
            ]})
        if path.endswith("/111_222"):
            body = {"id": "111_222", "comments": {"data": [], "summary": {"total_count": 5}}}
            if shares:
                body["shares"] = {"count": 2}
            return httpx.Response(200, json=body)
        return httpx.Response(404, json={})
    return handler


def test_facebook_post_id_success_sums_reactions():
    (state, metrics, extra), requests = _read(meta.read_facebook_post, "111_222", _facebook_handler())
    assert state == "ok"
    assert metrics == {"views": 500, "reach": 300, "likes": 10, "comments": 5, "shares": 2, "saves": None}
    assert extra["reactions_by_type"] == {"like": 7, "love": 3} and extra["measured_id"] == "111_222"
    assert "post_impressions" not in str([r.url for r in requests])
    assert all(TOKEN not in str(r.url) for r in requests)


def test_facebook_photo_id_resolves_to_page_story_and_missing_shares_is_none():
    (state, metrics, extra), _ = _read(meta.read_facebook_post, "333", _facebook_handler(shares=False))
    assert state == "ok" and extra["resolved_from"] == "photo" and extra["measured_id"] == "111_222"
    assert metrics["shares"] is None and metrics["comments"] == 5


def test_facebook_photo_without_story_and_video_are_not_invented():
    (state, metrics, _), _ = _read(meta.read_facebook_post, "333", _facebook_handler(story=None))
    assert state == "sem_id" and metrics is None
    (state, metrics, _), requests = _read(meta.read_facebook_post, "444", _facebook_handler())
    assert state == "unsupported_type" and metrics is None and len(requests) == 1


def test_facebook_removed_post_and_missing_scope():
    (state, _, _), _ = _read(meta.read_facebook_post, "111_222", lambda r: _error(100, 33))
    assert state == "not_found"
    (state, _, _), _ = _read(meta.read_facebook_post, "111_222", lambda r: _error(10, status=403))
    assert state == "permission_required"


def _fb_fields_fail(response):
    base = _facebook_handler()

    def handler(request):
        if request.url.path.endswith("/111_222") and request.url.params.get("fields") == meta.FB_POST_FIELDS:
            return response
        return base(request)
    return handler


def test_facebook_post_fields_permission_error_keeps_insights(caplog):
    caplog.set_level("WARNING", logger=meta.__name__)
    (state, metrics, extra), _ = _read(meta.read_facebook_post, "333", _fb_fields_fail(_error(10, status=403)))
    assert state == "ok"
    assert metrics == {"views": 500, "reach": 300, "likes": 10, "comments": None, "shares": None, "saves": None}
    assert extra["post_fields"] == {"state": "permission_required", "step": "post_fields",
                                    "graph_code": 10, "graph_subcode": None}
    assert "message" not in str(extra) and TOKEN not in str(extra) and "Requires" not in str(extra)
    log = caplog.text
    assert "code=10" in log and "status=403" in log and "type=OAuthException" in log
    assert TOKEN not in log and "Requires" not in log
    assert "111" not in log and "222" not in log and "333" not in log  # sem IDs de post/Página


def test_facebook_post_fields_stop_states_still_return_early():
    for response, expected in ((_error(190, status=401), "token_expired"), (_error(4), "rate_limited"),
                               (_error(100, 33), "not_found")):
        (state, metrics, extra), _ = _read(meta.read_facebook_post, "111_222", _fb_fields_fail(response))
        assert state == expected and metrics is None and extra["step"] == "post_fields"


def test_facebook_insights_error_records_step_and_code_without_message():
    def handler(request):
        if request.url.path.endswith("/insights"):
            return _error(10, status=403, message="(#10) Not enough viewers")
        return _facebook_handler()(request)
    (state, metrics, extra), _ = _read(meta.read_facebook_post, "333", handler)
    assert state == "access_denied" and metrics is None
    assert extra == {"resolved_from": "photo", "step": "insights", "graph_code": 10, "graph_subcode": None}
    (state, _, extra), _ = _read(meta.read_facebook_post, "333", lambda r: _error(200, 7))
    assert state == "permission_required"
    assert extra == {"step": "resolve", "graph_code": 200, "graph_subcode": 7}


def test_access_denied_does_not_stop_or_ask_reconnect(monkeypatch):
    jobs = [_job(f"fb{i}", "facebook", f"1{i}_2", post_id=i) for i in range(3)]
    states, persisted, history = _collect(
        monkeypatch, jobs, lambda r: _error(10, status=403, message="(#10) Not enough viewers"))
    assert states["facebook"] == "access_denied" and "access_denied" not in meta.STOP_STATES
    assert "access_denied" not in meta.RECONNECT_STATES
    assert len(history) == 3 and all(row["extra"]["graph_code"] == 10 for row in history)
    assert all(row["extra"]["step"] == "insights" for row in history)
    assert TOKEN not in str(history)


# ---------------- Coletor ----------------

def _job(job_id, network, external, post_id=1):
    return {"id": job_id, "post_id": post_id, "profile_id": "profile-a", "network": network,
            "external_id": external, "finished_at": "2026-11-13T10:00:00+00:00"}


def _collect(monkeypatch, jobs, handler, accounts=None):
    persisted, history = [], []
    accounts = accounts if accounts is not None else {"instagram": "cipher", "facebook": "cipher"}
    monkeypatch.setattr(post_insights, "_profile_jobs", lambda *a: jobs)
    monkeypatch.setattr(post_insights, "_meta_account", lambda network, *a: accounts.get(network))
    monkeypatch.setattr(post_insights, "_threads_account", lambda *a: None)
    monkeypatch.setattr(post_insights, "decrypt", lambda value: TOKEN)
    monkeypatch.setattr(post_insights, "_persist",
                        lambda job, user, state, metrics: persisted.append((job["id"], state, metrics)))
    monkeypatch.setattr(post_insights, "_record_history", history.append)
    real = httpx.AsyncClient
    monkeypatch.setattr(post_insights.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    states = asyncio.run(post_insights.collect_profile_posts("user-a", "profile-a"))
    return states, persisted, history


def test_collector_records_instagram_and_facebook_history(monkeypatch):
    def handler(request):
        if "/1789/" in request.url.path:
            return httpx.Response(200, json=IG_OK)
        return _facebook_handler()(request)
    jobs = [_job("ig1", "instagram", "1789"), _job("fb1", "facebook", "333", post_id=2)]
    states, persisted, history = _collect(monkeypatch, jobs, handler)
    assert states["instagram"] == "ok" and states["facebook"] == "ok"
    assert states["tiktok"] == "unsupported" and states["x"] == "unsupported"
    rows = {row["publish_job_id"]: row for row in history}
    assert rows["ig1"]["source"] == "ig_media_insights" and rows["ig1"]["saves"] == 2
    assert rows["ig1"]["reach"] == 90 and rows["ig1"]["clicks"] is None
    assert rows["fb1"]["source"] == "fb_post_insights" and rows["fb1"]["external_id"] == "111_222"
    assert rows["fb1"]["likes"] == 10 and rows["fb1"]["extra"]["resolved_from"] == "photo"
    assert ("ig1", "ok") in [(job, state) for job, state, _ in persisted]
    assert TOKEN not in str(history) and TOKEN not in str(persisted)


def test_missing_scope_stops_calls_but_records_every_post(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return _error(10, status=403)
    jobs = [_job(f"ig{i}", "instagram", f"17{i}", post_id=i) for i in range(6)]
    states, persisted, history = _collect(monkeypatch, jobs, handler)
    assert states["instagram"] == "permission_required"
    assert len(history) == 6 and all(row["status"] == "permission_required" for row in history)
    assert len(persisted) == 6  # a UI mostra "reconecte a conta" em cada post
    assert len(calls) <= post_insights._PARALLEL  # não martela a API depois do primeiro erro


def test_rate_limit_keeps_last_cached_value(monkeypatch):
    jobs = [_job("ig1", "instagram", "1789"), _job("ig2", "instagram", "1790", post_id=2)]
    states, persisted, history = _collect(monkeypatch, jobs, lambda r: _error(4))
    assert states["instagram"] == "rate_limited"
    assert persisted == []  # cache anterior não é apagado
    assert {row["status"] for row in history} == {"rate_limited"}


def test_expired_token_on_one_network_never_breaks_the_other(monkeypatch):
    def handler(request):
        if "/1789/" in request.url.path:
            return _error(190, status=401)
        return _facebook_handler()(request)
    jobs = [_job("ig1", "instagram", "1789"), _job("fb1", "facebook", "111_222", post_id=2)]
    states, _, history = _collect(monkeypatch, jobs, handler)
    assert states["instagram"] == "token_expired" and states["facebook"] == "ok"
    assert {row["publish_job_id"]: row["status"] for row in history} == {"ig1": "token_expired", "fb1": "ok"}


def test_crash_in_one_network_is_contained(monkeypatch):
    def boom(*args):
        raise RuntimeError("db down")
    jobs = [_job("ig1", "instagram", "1789"), _job("fb1", "facebook", "111_222", post_id=2)]
    monkeypatch.setattr(post_insights, "_meta_account",
                        lambda network, *a: boom() if network == "instagram" else "cipher")
    monkeypatch.setattr(post_insights, "_profile_jobs", lambda *a: jobs)
    monkeypatch.setattr(post_insights, "decrypt", lambda value: TOKEN)
    monkeypatch.setattr(post_insights, "_persist", lambda *a: None)
    monkeypatch.setattr(post_insights, "_record_history", lambda row: None)
    real = httpx.AsyncClient
    monkeypatch.setattr(post_insights.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(_facebook_handler()), **kw))
    states = asyncio.run(post_insights.collect_profile_posts("user-a", "profile-a"))
    assert states["instagram"] == "unavailable" and states["facebook"] == "ok"


def test_not_connected_network_makes_no_calls(monkeypatch):
    calls = []
    states, persisted, history = _collect(
        monkeypatch, [_job("fb1", "facebook", "111_222")],
        lambda r: calls.append(r) or httpx.Response(200, json={}), accounts={})
    assert states["facebook"] == "not_connected" and not calls and not history and not persisted
