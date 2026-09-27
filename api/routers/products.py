"""
Products Router — API Python (FastAPI)
CRUD completo de produtos da Shopee com Supabase.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Any

from .auth import get_current_user_id
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

def _get(user_id: int, product_id: int) -> dict[str, Any]:
    """Busca um produto pelo ID, verificando ownership."""
    result = (
        supabase.table("products")
        .select("*")
        .eq("id", product_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return result.data


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_products(
    user_id: int = Depends(get_current_user_id),
    search: str | None = Query(None, description="Busca por nome"),
    category: str | None = Query(None, description="Filtrar por categoria"),
    min_price: float | None = Query(None, description="Preço mínimo"),
    max_price: float | None = Query(None, description="Preço máximo"),
    sort_by: str = Query("created_at", description="Campo de ordenação"),
    sort_order: str = Query("desc", description="Ordem: asc ou desc"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(50, ge=1, le=200, description="Itens por página"),
):
    """Lista produtos com filtros, ordenação e paginação por offset."""
    query = supabase.table("products").select("*").eq("user_id", user_id)

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
        "data": result.data,
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
    result = (
        supabase.table("products")
        .insert({
            "user_id": user_id,
            "product_id": body.product_id,
            "name": body.name,
            "original_link": body.original_link,
            "commission_link": body.commission_link,
            "commission": body.commission,
            "image": body.image,
            "price_min": body.price_min,
            "price_max": body.price_max,
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar produto")
    return result.data[0]


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
    """Atualiza um produto existente."""
    _get(user_id, product_id)  # ownership check

    update_data: dict[str, Any] = {}
    for key, value in body.model_dump(exclude_unset=True).items():
        update_data[key] = value

    result = (
        supabase.table("products")
        .update(update_data)
        .eq("id", product_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return result.data


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Remove um produto."""
    _get(user_id, product_id)  # ownership check

    result = (
        supabase.table("products")
        .delete()
        .eq("id", product_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return {"msg": "Produto removido"}
