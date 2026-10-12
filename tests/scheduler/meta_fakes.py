"""Fakes estritos para os testes dos publicadores Meta: assinatura real,
falha em qualquer chamada não prevista (nada de MagicMock aceitando tudo)."""


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = str(self._payload)

    def json(self):
        return self._payload


class FakeGraph:
    """Substitui requests.get/post. `routes` mapeia (método, url) para uma
    lista de respostas consumidas em ordem (a última se repete)."""

    def __init__(self, routes):
        self.routes = {key: list(value) for key, value in routes.items()}
        self.calls = []

    def _handle(self, method, url, params, data, json, timeout):
        self.calls.append({"method": method, "url": url, "params": params, "data": data, "json": json})
        queue = self.routes.get((method, url))
        if not queue:
            raise AssertionError(f"chamada inesperada: {method} {url} {params}")
        response = queue.pop(0) if len(queue) > 1 else queue[0]
        return response if isinstance(response, FakeResponse) else FakeResponse(response)

    def get(self, url, params=None, timeout=None):
        return self._handle("GET", url, params, None, None, timeout)

    def post(self, url, params=None, data=None, json=None, timeout=None):
        return self._handle("POST", url, params, data, json, timeout)

    def urls(self, method):
        return [c["url"] for c in self.calls if c["method"] == method]


class FakeBucket:
    def __init__(self, store, bucket):
        self.store, self.bucket = store, bucket

    def create_signed_url(self, path, expires_in):
        self.store.signed.append((self.bucket, path, expires_in))
        url = f"https://signed.example/{self.bucket}/{path}?token=t"
        return {"signedURL": url, "signedUrl": url}


class FakeStorage:
    def __init__(self):
        self.signed = []

    def from_(self, bucket):
        return FakeBucket(self, bucket)
