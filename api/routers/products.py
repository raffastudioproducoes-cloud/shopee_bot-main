"""
Products Router — API Python (FastAPI)
CRUD completo de produtos da Shopee com Supabase.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Any

from .auth import get_current_user_id
from .profiles import get_current_profile_id
from ..audit_trail import record_audit_event
from ..database import supabase

router = APIRouter(prefix="/products", tags=["products"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    product_id: str
    name: str
    original_link: str | None = None
    commission_link: str | None = None
    commission: float | None = None
    image: str | None = None
    price_min: float | None = None
    price_max: float | None = None


class ProductUpdate(BaseModel):
    product_id: str | None = None
    name: str | None = None
    original_link: str | None = None
    commission_link: str | None = None
    commission: float | None = None
    image: str | None = None
    price_min: float | None = None
    price_max: float | None = None


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


def _get(user_id: int, product_id: int, profile_id: str | None = None) -> dict[str, Any]:
    """Busca um produto pelo ID, verificando ownership.

    `profile_id` opcional (fallback pra token antigo sem essa claim)."""
    query = (
        supabase.table("products")
        .select("*")
        .eq("id", product_id)
        .eq("user_id", user_id)
    )
    if profile_id:
        query = query.eq("profile_id", profile_id)
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


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_products(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    search: str | None = Query(None, description="Busca por nome"),
    category: str | None = Query(None, description="Filtrar por categoria"),
    min_price: float | None = Query(None, description="Preço mínimo"),
    max_price: float | None = Query(None, description="Preço máximo"),
    sort_by: str = Query("created_at", description="Campo de ordenação"),
    sort_order: str = Query("desc", description="Ordem: asc ou desc"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(50, ge=1, le=200, description="Itens por página"),
):
    """Lista produtos com filtros, ordenação e paginação por offset.

    `profile_id` é opcional: tokens antigos (sem essa claim) continuam
    filtrando só por `user_id` (fallback, nunca quebra sessão existente)."""
    query = supabase.table("products").select("*").eq("user_id", user_id)
    if profile_id:
        query = query.eq("profile_id", profile_id)

    if search:
        query = query.ilike("name", f"%{search}%")
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
    profile_id: str | None = Depends(get_current_profile_id),
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
    if profile_id:
        data["profile_id"] = profile_id
    duplicate = HTTPException(status_code=409, detail="Produto já cadastrado neste perfil")
    if find_product_in_profile(supabase, user_id, body.product_id, profile_id):
        raise duplicate
    try:
        result = supabase.table("products").insert(data).execute()
    except Exception as exc:  # corrida: o índice único (041) é a barreira final
        if "23505" in str(exc) or "duplicate key" in str(exc).lower():
            raise duplicate from exc
        raise
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar produto")
    return _normalize_numeric_fields(result.data[0])


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Retorna um produto específico."""
    return _get(user_id, product_id, profile_id)


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    body: ProductUpdate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Atualiza um produto existente."""
    before = _get(user_id, product_id, profile_id)  # ownership check

    update_data: dict[str, Any] = {}
    for key, value in body.model_dump(exclude_unset=True).items():
        update_data[key] = value

    update_query = (
        supabase.table("products")
        .update(update_data)
        .eq("id", product_id)
        .eq("user_id", user_id)
    )
    if profile_id:
        update_query = update_query.eq("profile_id", profile_id)
    result = update_query.single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    after = _normalize_numeric_fields(result.data)

    price_fields = ("price_min", "price_max")
    if any(before.get(field) != after.get(field) for field in price_fields):
        record_audit_event(
            entity="product",
            entity_id=str(product_id),
            user_id=str(user_id),
            action="product_price_changed",
            old_value={field: before.get(field) for field in price_fields},
            new_value={field: after.get(field) for field in price_fields},
            profile_id=profile_id,
        )

    return after


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Remove um produto."""
    before = _get(user_id, product_id, profile_id)  # ownership check

    delete_query = (
        supabase.table("products")
        .delete()
        .eq("id", product_id)
        .eq("user_id", user_id)
    )
    if profile_id:
        delete_query = delete_query.eq("profile_id", profile_id)
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
        profile_id=profile_id,
    )

    return {"msg": "Produto removido"}
