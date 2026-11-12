"""S-01 (auditoria 07/11/2026): catraca de rotas com ID de recurso no caminho.

O que este teste FAZ: congela o inventário das rotas que recebem um ID (ou nome de recurso)
no caminho. Se uma rota com `{parametro}` for criada ou removida, o teste falha e obriga quem
mexeu a revisar o escopo por conta/perfil (`scope_owner`/`scope_account`/`user_id` explícito) e a
atualizar esta lista no mesmo PR.

A prova de que cada rota nega A -> B está em tests/api/test_s01_ab_matrix.py (matriz dinâmica com
contas fictícias A/B; ela exige que toda rota deste inventário tenha caso de teste).
Helpers de thread de posts: tests/api/test_s01_post_scope.py.
"""
import re

from api.main import app

# Inventário em 09/11/2026 (GET/POST/PUT/DELETE com parametro no caminho).
REVIEWED_ID_ROUTES = frozenset({
    "DELETE /admin/ai/{provider}",
    "DELETE /admin/users/{user_id}",
    "DELETE /campaigns/drafts/{draft_id}",
    "DELETE /campaigns/drafts/{draft_id}/media/{media_id}",
    "DELETE /credentials/ai/{provider}",
    "DELETE /credentials/{network}",
    "DELETE /lists/{product_list_id}",
    "DELETE /posts/media-drafts/{media_id}",
    "DELETE /posts/{post_id}",
    "DELETE /posts/{post_id}/media/{media_id}",
    "DELETE /products/{product_id}",
    "DELETE /products/{product_id}/media/{asset_id}",
    "DELETE /profiles/{profile_id}",
    "GET /admin/users/{user_id}",
    "GET /campaigns/active/{reservation_id}",
    "GET /campaigns/active/{reservation_id}/history",
    "GET /campaigns/drafts/{draft_id}",
    "GET /campaigns/drafts/{draft_id}/media",
    "GET /campaigns/drafts/{draft_id}/preflight",
    "GET /lists/{product_list_id}",
    "GET /posts/{post_id}",
    "GET /posts/{post_id}/future-revisions/latest",
    "GET /products/{product_id}",
    "GET /products/{product_id}/image/download",
    "GET /products/{product_id}/media",
    "GET /products/{product_id}/media/{asset_id}/thumbnail",
    "GET /products/{product_id}/shopee-gallery-probe",
    "POST /admin/ai/{provider}/activate",
    "POST /admin/ai/{provider}/test",
    "POST /admin/users/{user_id}/erasure/retry",
    "POST /campaigns/active/{reservation_id}/{action}",
    "POST /campaigns/drafts/{draft_id}/activate",
    "POST /campaigns/drafts/{draft_id}/items/{product_id}/media",
    "POST /credentials/ai/{provider}/test",
    "POST /credentials/{network}/test",
    "POST /posts/product-image-drafts/{product_id}",
    "POST /posts/{post_id}/future-revisions",
    "POST /posts/{post_id}/media",
    "POST /posts/{post_id}/publish",
    "POST /posts/{post_id}/reconcile",
    "POST /posts/{post_id}/retry-unknown",
    "POST /products/{product_id}/media",
    "POST /profiles/{profile_id}/activate",
    "POST /profiles/{profile_id}/avatar",
    "PUT /admin/ai/{provider}",
    "PUT /admin/users/{user_id}",
    "PUT /admin/users/{user_id}/plan",
    "PUT /campaigns/drafts/{draft_id}",
    "PUT /credentials/ai/{provider}",
    "PUT /credentials/{network}",
    "PUT /lists/{product_list_id}",
    "PUT /posts/{post_id}",
    "PUT /products/{product_id}",
    "PUT /profiles/{profile_id}",
})


def _current_id_routes() -> set[str]:
    paths = app.openapi()["paths"]
    return {
        f"{method.upper()} {path}"
        for path, operations in paths.items() if re.search(r"\{\w+\}", path)
        for method in operations if method in ("get", "post", "put", "patch", "delete")
    }


def test_no_new_id_route_without_scope_review():
    novas = sorted(_current_id_routes() - REVIEWED_ID_ROUTES)
    assert not novas, (
        "Rota(s) nova(s) com ID no caminho: revise o escopo por conta/perfil (S-01), "
        "adicione teste A/B e inclua em REVIEWED_ID_ROUTES: %s" % novas
    )


def test_removed_id_routes_are_dropped_from_inventory():
    removidas = sorted(REVIEWED_ID_ROUTES - _current_id_routes())
    assert not removidas, "Remova do inventário as rotas que deixaram de existir: %s" % removidas
