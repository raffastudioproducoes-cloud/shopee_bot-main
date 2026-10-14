"""Fakes estritos da Graph API (sem rede) compartilhados pelos testes OAuth."""

import httpx  # noqa: F401

from api import instagram_oauth


class _Resp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._payload = payload
        self.text = "body"

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _install_graph_fake(monkeypatch, module, routes, calls):
    """routes: sufixo de URL -> _Resp | Exception. Falha se rota desconhecida."""

    class FakeClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return None

        async def get(self, url, **kwargs):
            calls.append((url, kwargs))
            for suffix, out in routes.items():
                if url.endswith(suffix):
                    if isinstance(out, Exception):
                        raise out
                    return out
            raise AssertionError(f"rota inesperada {url}")

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(instagram_oauth, "APP_ID", "appid")
    monkeypatch.setattr(instagram_oauth, "SECRET", "appsecret")


def _debug_resp(*target_sets):
    return _Resp({"data": {"granular_scopes": [
        {"scope": s, "target_ids": ids} for s, ids in target_sets
    ]}})
