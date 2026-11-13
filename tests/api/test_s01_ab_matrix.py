"""S-01: matriz A/B dinâmica — a conta A não lê nem altera recurso da conta B.

Para cada rota com ID de recurso no caminho, a conta A (autenticada) chama a rota apontando para
o ID de um recurso que pertence à conta B. O banco é um Supabase em memória que APLICA os filtros
de verdade (`eq`, `in_`, `is_`...), então uma rota que esquecer o filtro por dono devolve dados de B
ou muda uma linha de B, e o teste falha.

Garantias (por rota):
  1. a resposta de A é 403/404 (nunca 2xx, nunca 5xx);
  2. nenhuma linha de B muda (snapshot de todas as tabelas antes/depois);
  3. controle: o MESMO pedido feito por B chega ao handler (não é 401/403/404). Isso evita o falso
     verde de uma rota que responde 404 só porque o fake não tem a linha.

Rotas administrativas (`/admin/*`) não têm dono por ID: o teste exige que usuário comum receba 403.
Rotas `/credentials/{network|provider}` não recebem ID de outra conta (o parâmetro é o nome da
rede/provedor e o dono vem sempre do token); ficam cobertas por tests/api/test_credential_ownership.py.
"""
from __future__ import annotations

import copy
import io
import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from api.main import app
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id
from tests.api.test_s01_id_routes_ratchet import REVIEWED_ID_ROUTES

A, B = 1, 2
import os
RAISE = bool(os.environ.get("AB_RAISE"))
PA, PB = "00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000b2"
RID = 7                                            # id inteiro dos recursos de B
UID = "11111111-1111-4111-8111-111111111111"       # uuid dos recursos de B
UID2 = "22222222-2222-4222-8222-222222222222"

_NOW = "2026-11-09T12:00:00+00:00"


class _Result(SimpleNamespace):
    pass


class _Query:
    def __init__(self, db, table):
        self.db, self.table_name = db, table
        self.op, self.payload = "select", None
        self.filters: list = []
        self._one = None
        self.count_requested = False

    # --- construtores -------------------------------------------------
    def select(self, *_a, count=None, **_k):
        self.count_requested = bool(count)
        return self

    def insert(self, payload, *_a, **_k):
        self.op, self.payload = "insert", payload
        return self

    def upsert(self, payload, *_a, **_k):
        self.op, self.payload = "upsert", payload
        return self

    def update(self, payload, *_a, **_k):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def single(self):
        self._one = "single"  # como o PostgREST: 0 linhas => erro
        return self

    def maybe_single(self):
        self._one = "maybe"
        return self

    # --- filtros ------------------------------------------------------
    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self.filters.append(("neq", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in", col, list(vals)))
        return self

    def is_(self, col, val):
        self.filters.append(("is", col, None if val in ("null", None) else val))
        return self

    def not_is(self, col, val):
        self.filters.append(("not_is", col, None if val in ("null", None) else val))
        return self

    @property
    def not_(self):
        outer = self

        class _Not:
            def is_(self, col, val):
                return outer.not_is(col, val)

            def __getattr__(self, _n):
                return lambda *a, **k: outer

        return _Not()

    def __getattr__(self, name):
        # order/range/limit/gte/lte/ilike/or_/contains... não restringem para B.
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self

    # --- execução -----------------------------------------------------
    def _match(self, row):
        for kind, col, val in self.filters:
            cur = row.get(col)
            if kind == "eq" and str(cur) != str(val):
                return False
            if kind == "neq" and str(cur) == str(val):
                return False
            if kind == "in" and str(cur) not in {str(v) for v in val}:
                return False
            if kind == "is" and cur != val:
                return False
            if kind == "not_is" and cur == val:
                return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])
        self.db.calls.append((self.table_name, self.op, list(self.filters)))
        if self.op == "select":
            hit = [copy.deepcopy(r) for r in rows if self._match(r)]
            if self._one:
                if not hit and self._one == "single":
                    raise APIError({"message": "JSON object requested, multiple (or no) rows returned",
                                    "code": "PGRST116", "details": "The result contains 0 rows", "hint": None})
                return _Result(data=hit[0] if hit else None, count=len(hit))
            return _Result(data=hit, count=len(hit))
        if self.op in ("insert", "upsert"):
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            new = [dict(i, id=i.get("id", len(rows) + 1000)) for i in items]
            rows.extend(new)
            return _Result(data=copy.deepcopy(new), count=len(new))
        if self.op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self.payload)
            return _Result(data=copy.deepcopy(hit), count=len(hit))
        hit = [r for r in rows if self._match(r)]
        self.db.tables[self.table_name] = [r for r in rows if not self._match(r)]
        return _Result(data=copy.deepcopy(hit), count=len(hit))


class _Storage:
    def from_(self, _bucket):
        return self

    def __getattr__(self, _n):
        return lambda *a, **k: SimpleNamespace(data=None, path="x", signed_url="https://x.invalid/s")


class _Rpc:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def execute(self):
        self.db.calls.append(("rpc:" + self.name, "rpc", []))
        return _Result(data=None, count=0)


class FakeDB:
    def __init__(self):
        self.calls: list = []
        self.storage = _Storage()
        self.tables = _seed()

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, _params=None, *a, **k):
        return _Rpc(self, name)


def _owned(extra: dict, owner=B, profile=PB):
    base = {"user_id": owner, "profile_id": profile, "created_at": _NOW, "updated_at": _NOW}
    base.update(extra)
    return base


def _seed() -> dict[str, list[dict]]:
    return {
        "users": [
            {"id": A, "username": "a", "is_admin": False, "role": "user", "access": "USER", "plan_tier": "premium"},
            {"id": B, "username": "b", "is_admin": False, "role": "user", "access": "USER", "plan_tier": "premium"},
        ],
        "profiles": [
            {"id": PA, "user_id": A, "kind": "principal", "name": "A", "plan_tier": "premium", "is_active": True,
             "created_at": _NOW},
            {"id": PB, "user_id": B, "kind": "principal", "name": "B", "plan_tier": "premium", "is_active": True,
             "created_at": _NOW},
            {"id": UID2, "user_id": B, "kind": "secundario", "name": "B2", "plan_tier": "premium", "is_active": True,
             "created_at": _NOW},
        ],
        "products": [_owned({"id": RID, "product_id": "100", "name": "Produto B", "image_url": None,
                             "price": 10, "url": "https://shopee.com.br/produto-i.1.100"})],
        "product_media": [_owned({"id": UID, "product_id": RID, "storage_path": "b/x.jpg", "kind": "image",
                                  "media_type": "image", "content_type": "image/jpeg", "status": "ready"})],
        "product_lists": [_owned({"id": RID, "name": "Lista B"})],
        "product_lists_products": [{"product_list_id": RID, "product_id": RID, "user_id": B}],
        "posts": [_owned({"id": RID, "post_id": None, "text": "Post B", "status": "draft", "network": "x",
                          "networks": ["x"], "scheduled_at": None, "published_at": None,
                          "created_at": _NOW})],
        "posts_medias": [_owned({"id": RID, "post_id": RID, "media_id": RID, "storage_path": "b/p.jpg"})],
        "medias": [_owned({"id": RID, "storage_path": "b/m.jpg", "content_type": "image/jpeg"})],
        "posts_products": [{"post_id": RID, "product_id": RID, "user_id": B}],
        "temporary_media_uploads": [_owned({"id": UID, "storage_path": "b/t.jpg", "content_type": "image/jpeg",
                                            "status": "ready"})],
        "campaign_drafts": [_owned({"id": UID, "name": "Camp B", "status": "draft", "revision": 1, "items": [],
                                    "networks": ["x"], "payload": {}})],
        "campaign_draft_media": [_owned({"id": UID, "campaign_id": UID, "product_id": RID, "status": "ready",
                                         "storage_bucket": "media-drafts",
                                         "storage_key": f"campaigns/{B}/{PB}/{UID}/c.jpg",
                                         "content_type": "image/jpeg"})],
        "campaign_reservations_f4e": [_owned({"id": UID, "draft_id": UID, "lifecycle": "active",
                                              "draft_snapshot": {"campaign_name": "Camp B"}})],
        "campaign_progress_f4e": [_owned({"reservation_id": UID, "done": 0})],
        "campaign_network_slots_f4e": [_owned({"id": UID2, "reservation_id": UID, "network": "x"})],
        "schedulers": [_owned({"id": RID, "status": True})],
        "publish_jobs": [_owned({"id": RID, "post_id": RID, "status": "unknown"})],
        "post_content_revisions": [_owned({"id": UID, "post_id": RID})],
        "x_credentials": [_owned({"id": RID})],
        "plan_limits": [{"tier": "premium", "active_campaigns_per_profile": 1, "campaign_days": 7,
                         "campaign_posts_per_day": 3, "automation_enabled": True}],
        "activities": [],
    }


# --- rotas ---------------------------------------------------------------
def _png():
    return {"file": ("a.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 32), "image/png")}


# (método, caminho com ID de B, kwargs do pedido). Corpo mínimo válido para chegar ao handler.
RESOURCE_CASES = [
    ("GET", f"/products/{RID}", {}),
    ("PUT", f"/products/{RID}", {"json": {"name": "hack"}}),
    ("DELETE", f"/products/{RID}", {}),
    ("GET", f"/products/{RID}/image/download", {}),
    ("GET", f"/products/{RID}/media", {}),
    ("POST", f"/products/{RID}/media", {"files": _png()}),
    ("GET", f"/products/{RID}/media/{UID}/thumbnail", {}),
    ("DELETE", f"/products/{RID}/media/{UID}", {}),
    ("GET", f"/products/{RID}/shopee-gallery-probe", {}),
    ("GET", f"/lists/{RID}", {}),
    ("PUT", f"/lists/{RID}", {"json": {"name": "hack"}}),
    ("DELETE", f"/lists/{RID}", {}),
    ("GET", f"/posts/{RID}", {}),
    ("PUT", f"/posts/{RID}", {"json": {"texts": ["hack"]}}),
    ("DELETE", f"/posts/{RID}", {}),
    ("POST", f"/posts/{RID}/publish", {}),
    ("POST", f"/posts/{RID}/media", {"files": _png()}),
    ("DELETE", f"/posts/{RID}/media/{RID}", {}),
    ("POST", f"/posts/{RID}/reconcile", {"json": {}}),
    ("POST", f"/posts/{RID}/retry-unknown", {"json": {"source_job_id": UID}}),
    ("POST", f"/posts/{RID}/future-revisions", {"json": {"texts": ["hack"]}}),
    ("GET", f"/posts/{RID}/future-revisions/latest", {}),
    ("POST", f"/posts/product-image-drafts/{RID}", {}),
    ("POST", f"/posts/product-media-drafts/{RID}/{UID}", {}),
    ("DELETE", f"/posts/media-drafts/{UID}", {}),
    ("GET", f"/campaigns/drafts/{UID}", {}),
    ("PUT", f"/campaigns/drafts/{UID}", {"json": {"name": "hack", "expected_revision": 1, "items": [
        {"product_id": RID, "title": "t", "copy": "c"}]}}),
    ("DELETE", f"/campaigns/drafts/{UID}?expected_revision=1", {}),
    ("GET", f"/campaigns/drafts/{UID}/preflight?expected_revision=1", {}),
    ("GET", f"/campaigns/drafts/{UID}/media", {}),
    ("POST", f"/campaigns/drafts/{UID}/items/{RID}/media", {"files": _png()}),
    ("DELETE", f"/campaigns/drafts/{UID}/media/{UID}", {}),
    ("POST", f"/campaigns/drafts/{UID}/activate", {"json": {"expected_revision": 1}}),
    ("GET", f"/campaigns/active/{UID}", {}),
    ("GET", f"/campaigns/active/{UID}/history", {}),
    ("POST", f"/campaigns/active/{UID}/pause", {}),
    ("PUT", f"/profiles/{UID2}", {"json": {"nome": "hack"}}),
    ("DELETE", f"/profiles/{UID2}", {}),
    ("POST", f"/profiles/{UID2}/activate", {}),
    ("POST", f"/profiles/{UID2}/avatar", {"files": _png()}),
]

ADMIN_CASES = [
    ("GET", "/admin/users/2", {}),
    ("PUT", "/admin/users/2", {"json": {"role": "admin"}}),
    ("DELETE", "/admin/users/2", {}),
    ("POST", "/admin/users/2/erasure/retry", {}),
    ("PUT", "/admin/users/2/plan", {"json": {"plan": "pro", "days": 5}}),
    ("PUT", "/admin/ai/openai", {"json": {"api_key": "k"}}),
    ("DELETE", "/admin/ai/openai", {}),
    ("POST", "/admin/ai/openai/activate", {}),
    ("POST", "/admin/ai/openai/test", {}),
]

CREDENTIAL_COVERED_ELSEWHERE = [
    ("PUT", "/credentials/{network}"), ("DELETE", "/credentials/{network}"),
    ("POST", "/credentials/{network}/test"), ("PUT", "/credentials/ai/{provider}"),
    ("DELETE", "/credentials/ai/{provider}"), ("POST", "/credentials/ai/{provider}/test"),
]


def _normalize(method: str, path: str) -> str:
    """Troca os IDs concretos pelos nomes de parâmetro para comparar com o inventário."""
    path = path.split("?")[0]
    p = path.replace(UID2, "{profile_id}")
    for tpl in REVIEWED_ID_ROUTES:
        m, _, pat = tpl.partition(" ")
        if m != method:
            continue
        rx = "^" + re.sub(r"\{\w+\}", r"[^/]+", pat) + "$"
        if re.match(rx, path):
            if pat.startswith("/campaigns/active/{reservation_id}/{action}") or "/{" in pat:
                return tpl
    return f"{method} {p}"


def _snapshot(db: FakeDB):
    return copy.deepcopy(db.tables)


def _b_rows(tables):
    out = {t: [r for r in rows if str(r.get("user_id")) == str(B)] for t, rows in tables.items()}
    return {t: rows for t, rows in out.items() if rows}


@pytest.fixture
def world(monkeypatch):
    db = FakeDB()
    import sys
    for name, mod in list(sys.modules.items()):
        if name.startswith("api.") and mod is not None and hasattr(mod, "supabase"):
            monkeypatch.setattr(mod, "supabase", db, raising=False)
    from api import database
    monkeypatch.setattr(database, "supabase", db, raising=False)
    monkeypatch.setattr(database, "get_supabase", lambda: db)
    yield db
    app.dependency_overrides.clear()


def _client(user, profile):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: user
    app.dependency_overrides[get_current_profile_id] = lambda: profile
    return TestClient(app, raise_server_exceptions=RAISE)


def _call(client, method, path, kw):
    kw = dict(kw)
    if "files" in kw:  # reabre o buffer a cada chamada
        kw["files"] = _png()
    return client.request(method, path, **kw)


@pytest.mark.parametrize("method,path,kw", RESOURCE_CASES, ids=[f"{m} {p}" for m, p, _ in RESOURCE_CASES])
def test_account_a_cannot_touch_account_b_resource(world, method, path, kw):
    before = _b_rows(_snapshot(world))
    res = _call(_client(A, PA), method, path, kw)
    assert res.status_code in (403, 404), (
        f"{method} {path} como conta A devolveu {res.status_code}: {res.text[:200]}"
    )
    assert _b_rows(world.tables) == before, f"{method} {path}: A alterou dados de B"


@pytest.mark.parametrize("method,path,kw", RESOURCE_CASES, ids=[f"{m} {p}" for m, p, _ in RESOURCE_CASES])
def test_control_owner_b_reaches_the_handler(world, method, path, kw):
    """Sem este controle, um 404 de A poderia ser só 'o fake não tem a linha'."""
    res = _call(_client(B, PB), method, path, kw)
    if path.endswith("/activate") and path.startswith("/profiles/"):
        # Troca de perfil lê o cookie de sessão; sem ele o handler responde 401 DEPOIS de achar o perfil.
        assert res.status_code == 401 and "inexistente" in res.text
        return
    assert res.status_code not in (401, 403), f"{method} {path}: B (dono) foi negado: {res.status_code} {res.text[:160]}"
    assert res.status_code != 404 or "não encontrad" not in res.text.lower(), (
        f"{method} {path}: B (dono) recebeu 404 — o seed do teste não cobre este caminho: {res.text[:200]}"
    )


@pytest.mark.parametrize("method,path,kw", ADMIN_CASES, ids=[f"{m} {p}" for m, p, _ in ADMIN_CASES])
def test_regular_user_is_denied_on_admin_routes(world, method, path, kw):
    before = _snapshot(world)
    res = _call(_client(A, PA), method, path, kw)
    assert res.status_code == 403, f"{method} {path}: usuário comum recebeu {res.status_code}"
    assert world.tables == before


def test_matrix_covers_every_reviewed_id_route():
    """Toda rota do inventário tem caso A/B, caso admin ou justificativa explícita."""
    covered = {_normalize(m, p) for m, p, _ in RESOURCE_CASES + ADMIN_CASES}
    covered |= {f"{m} {p}" for m, p in CREDENTIAL_COVERED_ELSEWHERE}
    faltando = sorted(REVIEWED_ID_ROUTES - covered)
    assert not faltando, f"Rotas com ID sem teste A/B: {faltando}"
