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

import logging
import time

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .. import shopee_catalog
from ..crypto import decrypt
from ..database import supabase
from ..profiles import scope_owner

router = APIRouter(prefix="/products", tags=["catalog"])
logger = logging.getLogger(__name__)

# O frontend pagina client-side em blocos de 50 e pede até 150 de uma vez;
# cada chamada à Shopee vai com no máximo SHOPEE_PAGE_LIMIT (50) itens —
# pedidos maiores viram páginas sequenciais (ver shopee_catalog.search_products).
DEFAULT_SEARCH_LIMIT = shopee_catalog.SHOPEE_PAGE_LIMIT
MAX_SEARCH_LIMIT = 200
_INT32_MAX = 2**31 - 1

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


def _get_shopee_credential(user_id: int, profile_id: str | None = None) -> tuple[str, str] | None:
    """Busca e descifra app_id/secret da Shopee do usuário autenticado —
    mesmo padrão de `api/routers/credentials.py::_test_payload` pra
    `SIMPLE_NETWORKS`. Com perfil ativo, usa a credencial DO PERFIL. None
    quando não há credencial salva/completa."""
    row = (
        scope_owner(supabase.table("shopee_credentials").select("app_id, secret"), user_id, profile_id)
        .maybe_single().execute()
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


def _error_status(exc: Exception) -> int:
    return 422 if isinstance(exc, shopee_catalog.ShopeeAuthError) else 502


def _error_detail(exc: Exception) -> str:
    """Mensagem específica por causa, sem detalhe interno/segredo."""
    if isinstance(exc, shopee_catalog.ShopeeAuthError):
        return ("Credencial da Shopee inválida, expirada ou sem acesso à API de afiliados. "
                "Reconecte em Credenciais.")
    if isinstance(exc, shopee_catalog.ShopeeRateLimitError):
        return "A Shopee limitou as buscas por alguns instantes. Aguarde um minuto e tente de novo."
    if exc.errors:
        return "A Shopee recusou a busca com esses filtros. Tente outra categoria/ordenação ou outro termo."
    return "A Shopee está indisponível no momento. Tente novamente em alguns minutos."


@router.get("/catalog-search")
async def catalog_search(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    keyword: str | None = Query(
        None, description="Termo de busca livre", max_length=MAX_KEYWORD_LENGTH,
    ),
    product_cat_id: int | None = Query(
        None, ge=1, le=_INT32_MAX, description="ID de categoria da Shopee (Int32)",
    ),
    sort_type: int = Query(
        1, description="1=Relevância, 2=Mais vendidos, 3=Preço desc, 4=Preço asc, 5=Comissão",
    ),
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
    page: int = Query(1, ge=1, le=100, description="Página da Shopee (tamanho = min(limit, 50))"),
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

    credential = _get_shopee_credential(user_id, profile_id)
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
            page=page,
        )
    except shopee_catalog.ShopeeCatalogError as exc:
        # Loga o motivo real (só message/code dos erros GraphQL, sem
        # credencial) — antes o 502 escondia a causa (Int64 x Int32).
        logger.warning(
            "catalog-search falhou (%s): %s errors=%s",
            type(exc).__name__, str(exc)[:200] if not exc.errors else "-",
            shopee_catalog.summarize_errors(exc.errors),
        )
        raise HTTPException(status_code=_error_status(exc), detail=_error_detail(exc))

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
