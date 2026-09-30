"""
Catálogo Shopee (Pesquisa Avançada) Router — API Python (FastAPI)

Busca produtos no catálogo REAL da Shopee (Affiliate Open API, ver
`api/shopee_catalog.py`) e lista categorias pro filtro — usado pela aba
"Pesquisa Avançada" de ProductsPage.tsx no frontend. Resultado não é
persistido aqui: o frontend chama `POST /products` (já existente) pra
adicionar um resultado ao catálogo pessoal do usuário.

Prefixo compartilhado com products.py ("/products") — registrado como
router separado (não dentro de products.py) porque a lógica de
credencial+GraphQL da Shopee não tem nada a ver com o CRUD Supabase de
products.py, e manter os dois num arquivo só passaria de 250 linhas.
"""

import time

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import get_current_user_id
from .. import shopee_catalog
from ..crypto import decrypt
from ..database import supabase

router = APIRouter(prefix="/products", tags=["catalog"])

# Limite alto o bastante pra paginação client-side (o frontend pagina em
# blocos de até 50), mas capado pra não abusar da API da Shopee — ela não
# tem paginação nativa (só `limit`), então cada busca é uma chamada só.
DEFAULT_SEARCH_LIMIT = 150
MAX_SEARCH_LIMIT = 200

# Tamanho máximo do termo de busca livre — sem isso, uma string arbitrária
# entra tanto na query GraphQL quanto no cálculo da assinatura sem limite
# (ver MEDIUM-1 do relatório de segurança).
MAX_KEYWORD_LENGTH = 200

# ponytail: rate limit de busca em memória de processo (mesmo padrão de
# `_check_login_rate_limit` em api/routers/auth.py) — por usuário
# autenticado, já que o endpoint exige login. Mesma limitação de lá: não
# escala pra múltiplos workers/instâncias. Upgrade: slowapi + Redis se a
# app crescer pra multi-worker.
_SEARCH_RATE_LIMIT_ATTEMPTS = 20
_SEARCH_RATE_LIMIT_WINDOW_SECONDS = 60
_search_attempts: dict[int, list[float]] = {}


def _check_search_rate_limit(user_id: int) -> None:
    now = time.monotonic()
    attempts = [
        t for t in _search_attempts.get(user_id, [])
        if now - t < _SEARCH_RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(attempts) >= _SEARCH_RATE_LIMIT_ATTEMPTS:
        _search_attempts[user_id] = attempts
        raise HTTPException(
            status_code=429,
            detail="Muitas buscas em pouco tempo. Aguarde antes de tentar novamente.",
        )
    attempts.append(now)
    _search_attempts[user_id] = attempts


def _get_shopee_credential(user_id: int) -> tuple[str, str] | None:
    """Busca e descifra app_id/secret da Shopee do usuário autenticado —
    mesmo padrão de `api/routers/credentials.py::_test_payload` pra
    `SIMPLE_NETWORKS`. None quando não há credencial salva/completa."""
    row = (
        supabase.table("shopee_credentials").select("app_id, secret")
        .eq("user_id", user_id).maybe_single().execute()
    )
    data = row.data if row and row.data else None
    if not data or not data.get("app_id") or not data.get("secret"):
        return None
    # .strip() defensivo (mesmo padrão de save_credential em credentials.py):
    # copiar/colar do painel da Shopee pode trazer espaço em branco.
    app_id = (data["app_id"] or "").strip()
    try:
        secret = (decrypt(data["secret"]) or "").strip()
    except InvalidToken:
        # Chave de criptografia rotacionada (ou dado corrompido) — erro
        # claro pro usuário, sem vazar detalhe interno da exceção
        # (ver LOW-2 do relatório de segurança).
        raise HTTPException(
            status_code=400,
            detail="Credencial da Shopee corrompida ou desatualizada. Reconecte-a em Credenciais.",
        )
    if not app_id or not secret:
        return None
    return app_id, secret


def _map_catalog_node(node: dict) -> dict:
    """Mapeia o retorno cru do GraphQL da Shopee pros campos que o frontend
    espera — quase 1:1 com o schema de `products` (ver
    database/migrations/002_create_products_table.sql), mais os campos
    best-effort (sales/rating_star/shop_name/commission_rate), que ficam
    None quando a Shopee não devolveu (fallback de schema, ver
    shopee_catalog.py)."""
    return {
        "product_id": node.get("itemId"),
        "name": node.get("productName"),
        "original_link": node.get("productLink"),
        "commission_link": node.get("offerLink"),
        "commission": node.get("commission"),
        "image": node.get("imageUrl"),
        "price_min": node.get("priceMin"),
        "price_max": node.get("priceMax"),
        "sales": node.get("sales"),
        "rating_star": node.get("ratingStar"),
        "shop_name": node.get("shopName"),
        "commission_rate": node.get("commissionRate"),
    }


@router.get("/catalog-search")
async def catalog_search(
    user_id: int = Depends(get_current_user_id),
    keyword: str | None = Query(
        None, description="Termo de busca livre", max_length=MAX_KEYWORD_LENGTH,
    ),
    product_cat_id: int | None = Query(None, description="ID de categoria da Shopee"),
    sort_type: int = Query(
        1, description="1=Relevância, 2=Mais vendidos, 3=Preço desc, 4=Preço asc, 5=Comissão",
    ),
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
):
    """Busca produtos no catálogo real da Shopee usando a credencial de
    afiliado do próprio usuário. Não persiste nada — o frontend decide o
    que adicionar via POST /products."""
    _check_search_rate_limit(user_id)

    if sort_type not in shopee_catalog.VALID_SORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="sort_type inválido. Use 1 (Relevância), 2 (Mais vendidos), "
                   "3 (Preço: maior→menor), 4 (Preço: menor→maior) ou 5 (Melhor comissão).",
        )

    credential = _get_shopee_credential(user_id)
    if credential is None:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma credencial da Shopee conectada. Configure em Credenciais antes de buscar produtos.",
        )
    app_id, secret = credential

    try:
        nodes = await shopee_catalog.search_products(
            app_id, secret,
            keyword=keyword,
            product_cat_id=product_cat_id,
            sort_type=sort_type,
            limit=limit,
        )
    except shopee_catalog.ShopeeAuthError:
        raise HTTPException(
            status_code=422,
            detail="Credencial da Shopee inválida ou sem permissão para buscar produtos.",
        )
    except shopee_catalog.ShopeeCatalogError:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível buscar produtos na Shopee agora. Tente novamente.",
        )

    return {"data": [_map_catalog_node(node) for node in nodes]}


@router.get("/catalog-categories")
async def catalog_categories(user_id: int = Depends(get_current_user_id)):
    """Árvore de categorias da Shopee pro filtro de categoria — não depende
    de credencial de afiliado (endpoint REST público da Shopee, ver
    shopee_catalog.py), só de o usuário estar autenticado no app."""
    try:
        categories = await shopee_catalog.get_category_list()
    except shopee_catalog.ShopeeCatalogError:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível buscar categorias da Shopee agora. Tente novamente.",
        )
    return {"data": categories}
