"""Regressões: nenhuma métrica de perfil/Página pode virar métrica de post."""
import asyncio

import httpx

from api import post_insights as insights


def test_threads_post_parser_preserves_zero_and_missing_values():
    result = insights.parse_threads_post_insights([
        {"name": "views", "total_value": {"value": 12}},
        {"name": "likes", "values": [{"value": 0}]},
        {"name": "replies", "total_value": {"value": 2}},
    ])
    assert result["views"] == 12
    assert result["likes"] == 0
    assert result["comments"] == 2
    assert result["clicks"] is None
    assert insights.parse_threads_post_insights([{"name": "views", "total_value": {"value": True}}]) is None
    assert insights.parse_threads_post_insights([{"name": "views", "values": [{"value": 1}, {"value": 2}]}]) is None


def test_only_confirmed_jobs_with_matching_network_and_id_are_summed():
    jobs = [
        {"id": "a", "network": "threads", "external_id": "42"},
        {"id": "b", "network": "threads", "external_id": "42"},  # Duplicated retry.
        {"id": "c", "network": "threads", "external_id": "99"},
        {"id": "d", "network": "threads", "external_id": None},
    ]
    cache = {
        "a": {"network": "threads", "external_id": "42", "state": "ok", "views": 14, "likes": 0},
        "b": {"network": "threads", "external_id": "42", "state": "ok", "views": 14},
        "c": {"network": "facebook", "external_id": "99", "state": "ok", "views": 31},
    }
    metrics, collected, eligible, states = insights.summarize_post_metrics(jobs, cache)
    assert metrics["views"] == 14
    assert metrics["likes"] == 0
    assert metrics["clicks"] is None
    assert collected == 1 and eligible == 2
    assert "not_collected" in states


def test_per_post_endpoint_never_calls_account_insights():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": [
            {"name": "views", "total_value": {"value": 4}},
        ]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await insights.read_threads_post(client, "123456789", "fake-token")

    state, metrics = asyncio.run(run())
    assert state == "ok" and metrics["views"] == 4
    assert len(requests) == 1
    assert requests[0].url.path == "/v1.0/123456789/insights"
    assert "threads_insights" not in str(requests[0].url)
    assert "123456789" in str(requests[0].url)


def test_invalid_external_id_never_goes_to_provider():
    class ForbiddenClient:
        async def get(self, *args, **kwargs):
            raise AssertionError("Untrusted ID must never reach a network call")

    state, data = asyncio.run(insights.read_threads_post(ForbiddenClient(), "bad/id", "token"))
    assert state == "invalid_id" and data is None
