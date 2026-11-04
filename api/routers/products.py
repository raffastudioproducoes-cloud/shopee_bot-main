"""
Products Router — API Python (FastAPI)
CRUD completo de produtos da Shopee com Supabase.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.product_search import product_search_filter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any

from .auth import get_current_user_id
from ..audit_trail import record_audit_event
from ..database import supabase
from ..network_limits import NETWORK_RULES, text_length
from ..profiles import scope_account

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)


# ── Pydantic schemas ──────────────────────────────────────────────────────────────

# `itemId` da Shopee chega como número (Int64) -> aceita e guarda como texto.
# `commission` = TAXA de comissão em % (6 = 6%), não o valor em R$.
class _ProductFields(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    @field_validator("commission", "price_min", "price_max", check_fields=False)
    @classmethod
    def _round_two_decimals(cls, value: float | None) -> float | None:
        return None if value is None else round(value, 2)

    @field_validator("product_id", check_fields=False)
    @classmethod
    def _require_numeric_shopee_product_id(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("product_id deve conter apenas dígitos")
        return value


class ProductCreate(_ProductFields):
    product_id: str
    name: str
    original_link: str = Field(min_length=1)
    commission_link: str = Field(min_length=1)
    commission: float | None = None
    image: str | None = None
    price_min: float | None = None
    price_max: float | None = None



class ProductUpdate(BaseModel):
    """Campos que o usuário pode personalizar sem afetar a comissão."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=280)

    @field_validator("name")
    @classmethod
    def _require_name(cls, value: str | None) -> str:
        if not value:
            raise ValueError("O nome não pode ficar vazio.")
        return value

    @field_validator("description")
    @classmethod
    def _short_copy_without_links(cls, value: str | None) -> str | None:
        if not value:
            return None
        if re.search(r"(?i)(?:https?://|www\.|(?:^|\s)(?:s\.shopee|shopee\.com|bit\.ly|t\.co)[^\s]*)", value):
            raise ValueError("A descrição não pode conter links; o link de comissão é separado.")
        if text_length(NETWORK_RULES["x"], value) > 280:
            raise ValueError("A descrição ultrapassa 280 caracteres ponderados (limite da rede mais curta).")
        return value


# ── Helpers ──────────────────────────────────────────────────────────────────────

# price_min/price_max/commission são TEXT na tabela `products` (schema legado do
# scraper Flask, ver database/migrations/002_create_products_table.sql) — o
# Postgrest devolve isso como string JSON (ex: "129.9"). O frontend (e o schema
# Pydantic acima) sempre tratou esses campos como número; sem essa conversão,
# `product.price_min.toFixed(2)` no ProductsPage.tsx quebra com
# "TypeError: toFixed is not a function" e derruba a página inteira.
_NUMERIC_FIELDS = ("price_min", "price_max", "commission")


def _normalize_numeric_fields(row: dict[str, Any]) -> dict[str, Any]:
    for field in _NUMERIC_FIELDS:
        value = row.get(field)
        if value is None or isinstance(value, (int, float)):
            continue
        try:
            row[field] = float(value)
        except (TypeError, ValueError):
            row[field] = None
    return row


def _get(user_id: int, product_id: int) -> dict[str, Any]:
    """Busca um produto compartilhado da conta pelo ID."""
    query = scope_account(supabase.table("products").select("*").eq("id", product_id), user_id)
    result = query.single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return _normalize_numeric_fields(result.data)


def find_product_in_profile(db: Any, user_id: Any, product_id: Any, profile_id: str | None) -> dict[str, Any] | None:
    """Produto da conta com esse `product_id` DENTRO do perfil (migração 041:
    a unicidade é por (user_id, product_id, perfil); sem perfil = linhas
    legadas com profile_id NULL)."""
    query = db.table("products").select("id").eq("user_id", user_id).eq("product_id", product_id)
    query = query.eq("profile_id", profile_id) if profile_id else query.is_("profile_id", "null")
    rows = query.limit(1).execute().data or []
    return rows[0] if rows else None


def find_product_in_account(db: Any, user_id: Any, product_id: Any) -> dict[str, Any] | None:
    query = scope_account(db.table("products").select("id").eq("product_id", product_id), user_id)
    rows = query.limit(1).execute().data or []
    return rows[0] if rows else None


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_products(
    user_id: int = Depends(get_current_user_id),
    search: str | None = Query(None, max_length=120, description="Busca por nome e termos relacionados"),
    category: str | None = Query(None, description="Filtrar por categoria"),
    min_price: float | None = Query(None, description="Preço mínimo"),
    max_price: float | None = Query(None, description="Preço máximo"),
    sort_by: str = Query("created_at", description="Campo de ordenação"),
    sort_order: str = Query("desc", description="Ordem: asc ou desc"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(50, ge=1, le=200, description="Itens por página"),
):
    """Lista produtos compartilhados da conta com paginação por offset."""
    query = scope_account(supabase.table("products").select("*"), user_id)

    if search is not None:
        filters = product_search_filter(search)
        if not filters:
            # Consulta vazia após saneamento: não remover o filtro por acidente.
            return {"data": [], "total": 0, "page": page, "page_size": page_size}
        query = query.or_(filters)
    if category:
        query = query.ilike("category", category)
    if min_price is not None:
        query = query.gte("price_min", min_price)
    if max_price is not None:
        query = query.lte("price_max", max_price)

    valid_sort_fields = {
        "created_at", "updated_at", "name", "price_min", "price_max",
        "commission", "product_id",
    }
    sort_field = sort_by if sort_by in valid_sort_fields else "created_at"
    order = "desc" if sort_order.lower() == "desc" else "asc"
    query = query.order(sort_field, desc=(order == "desc"))

    offset = (page - 1) * page_size
    result = query.range(offset, offset + page_size - 1).execute()

    return {
        "data": [_normalize_numeric_fields(row) for row in result.data],
        "total": len(result.data),
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    user_id: int = Depends(get_current_user_id),
):
    """Cria um novo produto."""
    data: dict[str, Any] = {
        "user_id": user_id,
        "product_id": body.product_id,
        "name": body.name,
        "original_link": body.original_link,
        "commission_link": body.commission_link,
        "commission": body.commission,
        "image": body.image,
        "price_min": body.price_min,
        "price_max": body.price_max,
    }
    duplicate = HTTPException(status_code=409, detail="Produto já cadastrado nesta conta")
    if find_product_in_account(supabase, user_id, body.product_id):
        raise duplicate
    try:
        # RPC atômica: bloqueio da linha da conta + contagem + INSERT na mesma transação.
        # Sem trigger global: a versão anterior em produção permanece compatível.
        result = supabase.rpc("insert_product_with_plan_quota", {
            "p_user_id": user_id, "p_product": data,
        }).execute()
    except Exception as exc:  # corrida: o índice único (041) é a barreira final
        if "plan_products_quota_exceeded" in str(exc):
            raise HTTPException(status_code=409, detail="Limite de produtos salvos do plano atingido.") from None
        if "plan_policy_unavailable" in str(exc):
            raise HTTPException(status_code=503, detail="Política do plano indisponível. Tente novamente.") from None
        if "23505" in str(exc) or "duplicate key" in str(exc).lower():
            raise duplicate from exc
        logger.error("Falha ao criar produto (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Falha ao criar produto") from None
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar produto")
    return _normalize_numeric_fields(result.data[0])


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Retorna um produto específico."""
    return _get(user_id, product_id)


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    body: ProductUpdate,
    user_id: int = Depends(get_current_user_id),
):
    """Somente nome e copy curta; preços, links, imagem Shopee e IDs são imutáveis."""
    _get(user_id, product_id)  # verificação da conta antes do UPDATE
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhuma alteração enviada.")
    result = scope_account(
        supabase.table("products").update(update_data).eq("id", product_id), user_id
    ).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return _normalize_numeric_fields(result.data)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Remove um produto."""
    before = _get(user_id, product_id)  # ownership check

    # Arquivos do produto não podem ficar órfãos no Storage após exclusão.
    from .product_media import remove_product_media_files
    remove_product_media_files(user_id, product_id)

    delete_query = scope_account(supabase.table("products").delete().eq("id", product_id), user_id)
    result = delete_query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    record_audit_event(
        entity="product",
        entity_id=str(product_id),
        user_id=str(user_id),
        action="product_deleted",
        old_value=before,
        new_value=None,
    )

    return {"msg": "Produto removido"}
