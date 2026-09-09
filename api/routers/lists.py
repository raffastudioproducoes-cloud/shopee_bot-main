"""
Listas de Produtos — API Python (FastAPI)
CRUD de listas de produtos da Shopee.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .auth import get_current_user_id
from ..database import supabase

router = APIRouter(prefix="/lists", tags=["lists"])


# ── Schemas ──────────────────────────────────────────────────────────────────────

class ProductListCreate(BaseModel):
    name: str


class ProductListUpdate(BaseModel):
    name: str


class ProductListOut(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str | None = None


class ProductListWithProducts(ProductListOut):
    products: list[dict] = []


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _get_list(user_id: int, product_list_id: int) -> dict:
    """Busca uma lista pelo ID, verificando ownership."""
    result = (
        supabase.table("product_lists")
        .select("*")
        .eq("id", product_list_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    return result.data


def _get_list_products(list_id: int) -> list[dict]:
    """Busca produtos de uma lista."""
    result = (
        supabase.table("product_lists_products")
        .select(
            "*, products(id, product_id, name, image, price_min, price_max, commission, commission_link, original_link)"
        )
        .eq("product_list_id", list_id)
        .execute()
    )
    products: list[dict] = []
    for item in result.data or []:
        product = item.get("products")
        if product:
            products.append(product)
    return products


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_product_lists(
    user_id: int = Depends(get_current_user_id),
    cursor: str | None = Query(None, description="Cursor de paginação"),
    limit: int = Query(20, ge=1, le=100, description="Tamanho da página"),
):
    """Lista listas de produtos com paginação por cursor."""
    query = (
        supabase.table("product_lists")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)

    result = query.execute()

    lists: list[dict] = []
    for item in result.data:
        products = _get_list_products(item["id"])
        lists.append({
            "id": item["id"],
            "name": item["name"],
            "created_at": item["created_at"],
            "updated_at": item.get("updated_at"),
            "products": products,
            "product_count": len(products),
        })

    # Determina próximo cursor
    next_cursor = None
    if result.data and len(result.data) == limit:
        last_item = result.data[-1]
        next_cursor = last_item["created_at"]

    return {"data": lists, "next_cursor": next_cursor}


@router.post("/")
async def create_product_list(
    body: ProductListCreate,
    user_id: int = Depends(get_current_user_id),
):
    """Cria uma nova lista de produtos."""
    result = (
        supabase.table("product_lists")
        .insert({"user_id": user_id, "name": body.name})
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar lista")
    return result.data[0]


@router.get("/{product_list_id}")
async def get_product_list(
    product_list_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Retorna uma lista específica com seus produtos."""
    list_data = _get_list(user_id, product_list_id)
    products = _get_list_products(product_list_id)
    return {
        "id": list_data["id"],
        "name": list_data["name"],
        "created_at": list_data["created_at"],
        "updated_at": list_data.get("updated_at"),
        "products": products,
        "product_count": len(products),
    }


@router.put("/{product_list_id}")
async def update_product_list(
    product_list_id: int,
    body: ProductListUpdate,
    user_id: int = Depends(get_current_user_id),
):
    """Atualiza o nome de uma lista."""
    result = (
        supabase.table("product_lists")
        .update({"name": body.name})
        .eq("id", product_list_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    return result.data


@router.delete("/{product_list_id}")
async def delete_product_list(
    product_list_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Remove uma lista de produtos."""
    result = (
        supabase.table("product_lists")
        .delete()
        .eq("id", product_list_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lista não encontrada")
    return {"msg": "Lista removida"}
