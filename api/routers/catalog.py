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
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import get_current_user_id
from .platform_shopee import get_affiliate_id, resolve_platform_shopee_key
from .. import shopee_catalog
from ..shopee_affiliate_links import build_affiliate_link
from ..rate_limiter import check_window
from ..database import supabase
from ..profiles import scope_account

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

# Rate limit de busca por usuário autenticado. Usa api/rate_limiter.py: Redis atômico quando
# RATELIMIT_STORAGE_URI está configurada; senão janela em memória com trava e chaves limitadas.
_SEARCH_RATE_LIMIT_ATTEMPTS = 20
_SEARCH_RATE_LIMIT_WINDOW_SECONDS = 60
_search_attempts: dict[int, list[float]] = {}


def _check_search_rate_limit(user_id: int) -> None:
    check_window(
        "catalog-search", user_id,
        attempts=_SEARCH_RATE_LIMIT_ATTEMPTS, window_seconds=_SEARCH_RATE_LIMIT_WINDOW_SECONDS,
        state=_search_attempts,
        detail="Muitas buscas em pouco tempo. Aguarde antes de tentar novamente.",
    )


def _get_shopee_credential(user_id: int) -> tuple[str, str] | None:
    """Catálogo global; o parâmetro legado não seleciona chaves de USER."""
    return resolve_platform_shopee_key()


def _to_float(value) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _commission_percent(node: dict) -> float | None:
    """Taxa de comissão em % (semântica de `products.commission`).

    Doc da Affiliate API (productOfferV2): `commissionRate` = taxa ("0.06" =
    6%) e `commission` = VALOR em moeda local (= preço × commissionRate).
    Sem `commissionRate` (fallback de schema), estima pela razão
    valor/preço máximo."""
    rate = _to_float(node.get("commissionRate"))
    if rate is not None:
        return round(rate * 100, 2)
    amount = _to_float(node.get("commission"))
    price = _to_float(node.get("priceMax")) or _to_float(node.get("priceMin"))
    if amount is None or not price:
        return None
    return round(amount / price * 100, 2)


def _map_catalog_node(node: dict, affiliate_id: str | None = None) -> dict:
    """Mapeia o retorno cru do GraphQL da Shopee pros campos que o frontend
    espera — quase 1:1 com o schema de `products` (ver
    database/migrations/002_create_products_table.sql). `commission` sai
    como TAXA em % e `commission_amount` como R$ por venda (só exibição).
    Campos best-effort (sales/rating_star/shop_name) ficam None quando a
    Shopee não devolveu (fallback de schema, ver shopee_catalog.py)."""
    amount = _to_float(node.get("commission"))
    item_id = node.get("itemId")
    return {
        "product_id": str(item_id) if item_id is not None else None,
        "name": node.get("productName"),
        "original_link": node.get("productLink"),
        # `offerLink` veio das credenciais ADMIN: jamais entregá-lo ao USER.
        "commission_link": build_affiliate_link(node.get("productLink"), affiliate_id),
        "commission": _commission_percent(node),
        "commission_amount": round(amount, 2) if amount is not None else None,
        "image": node.get("imageUrl"),
        "price_min": node.get("priceMin"),
        "price_max": node.get("priceMax"),
        "sales": node.get("sales"),
        "rating_star": node.get("ratingStar"),
        "shop_name": node.get("shopName"),
    }


def _error_status(exc: Exception) -> int:
    return 422 if isinstance(exc, shopee_catalog.ShopeeAuthError) else 502


def _error_detail(exc: Exception) -> str:
    """Mensagem específica por causa, sem detalhe interno/segredo."""
    if isinstance(exc, shopee_catalog.ShopeeAuthError):
        return "A API Shopee da plataforma precisa ser verificada pelo administrador."
    if isinstance(exc, shopee_catalog.ShopeeRateLimitError):
        return "A Shopee limitou as buscas por alguns instantes. Aguarde um minuto e tente de novo."
    if exc.errors:
        return "A Shopee recusou a busca com esses filtros. Tente outra categoria/ordenação ou outro termo."
    return "A Shopee está indisponível no momento. Tente novamente em alguns minutos."


@router.get("/catalog-search")
async def catalog_search(
    user_id: int = Depends(get_current_user_id),
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
    """Busca com API global, links personalizados somente para esta conta."""
    _check_search_rate_limit(user_id)

    if sort_type not in shopee_catalog.VALID_SORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="sort_type inválido. Use 1 (Relevância), 2 (Mais vendidos), "
                   "3 (Preço: maior→menor), 4 (Preço: menor→maior) ou 5 (Melhor comissão).",
        )

    affiliate_id = get_affiliate_id(user_id)
    if affiliate_id is None:
        raise HTTPException(
            status_code=400,
            detail="Cadastre seu ID de afiliado Shopee em Credenciais antes de buscar produtos.",
        )
    credential = _get_shopee_credential(user_id)
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

    return {"data": [_map_catalog_node(node, affiliate_id) for node in nodes]}


def _safe_shopee_gallery_url(value: object) -> bool:
    """As mesmas origens permitidas na importação privada do compositor."""
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and (host in {"cf.shopee.com.br", "down-br.img.susercontent.com",
                          "img.susercontent.com"}
                 or host.endswith(".img.susercontent.com"))
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
        )
    except (ValueError, TypeError):
        return False


@router.get("/{product_id}/shopee-gallery-probe")
async def shopee_gallery_probe(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Consulta sob demanda imagens do produto pela API oficial de afiliados.

    Não grava no banco, não importa mídia nem muda a seleção existente.
    Falha de probe não bloqueia upload local nem a imagem Shopee cadastrada.
    """
    _check_search_rate_limit(user_id)
    product = (
        scope_account(
            supabase.table("products")
            .select("id,product_id,image").eq("id", product_id),
            user_id,
        ).maybe_single().execute()
    )
    row = product.data if product else None
    if not row:
        raise HTTPException(status_code=404, detail="Produto não encontrado nesta conta.")

    saved = row.get("image")
    fallback = [saved] if _safe_shopee_gallery_url(saved) else []
    item_id = row.get("product_id")
    if not str(item_id or "").isdigit() or not 0 < int(item_id) < 2**63:
        return {
            "image_urls": fallback, "status": "not_identified",
            "message": "Produto sem itemId numérico; somente foto cadastrada disponível.",
        }
    try:
        credential = _get_shopee_credential(user_id)
    except HTTPException:
        return {
            "image_urls": fallback, "status": "not_connected",
            "message": "A API Shopee da plataforma está indisponível. O upload local continua disponível.",
        }
    try:
        result = await shopee_catalog.probe_product_gallery(
            *credential, item_id=int(item_id),
        )
    except shopee_catalog.ShopeeCatalogError as exc:
        logger.info("Probe galeria Shopee sem resultado (%s)", type(exc).__name__)
        return {
            "image_urls": fallback, "status": "unavailable",
            "message": "Não foi possível confirmar outras fotos na API agora. Você pode usar a imagem cadastrada ou enviar arquivos.",
        }
    urls = []
    for value in [*result["image_urls"], *fallback]:
        if _safe_shopee_gallery_url(value) and value not in urls:
            urls.append(value)
        if len(urls) >= 10:
            break
    status = "multiple" if len(urls) > 1 else result["status"]
    return {
        "image_urls": urls,
        "status": status,
        "field_tested": result["field_tested"],
        "message": (
            f"A API retornou {len(urls)} URLs de fotos para este produto; ainda é necessário validar cada arquivo antes de usar."
            if len(urls) > 1
            else "Nesta consulta a API não confirmou fotos adicionais. A imagem principal e os uploads locais continuam disponíveis."
        ),
    }


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
