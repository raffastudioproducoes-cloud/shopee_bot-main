"""
Listas de Produtos — API Python (FastAPI)
CRUD de listas de produtos da Shopee.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .auth import get_current_user_id
from .profiles import get_current_profile_id
from ..audit_trail import record_audit_event
from ..database import supabase
from ..profiles import scope_owner

router = APIRouter(prefix="/lists", tags=["lists"])


# ── Schemas ──────────────────────────────────────────────────────────────────────

class ProductListCreate(BaseModel):
    name: str


class ProductListUpdate(BaseModel):
    name: str
    product_ids: list[int] | None = None


class ProductListOut(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str | None = None


class ProductListWithProducts(ProductListOut):
    products: list[dict] = []


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _get_list(user_id: int, product_list_id: int, profile_id: str | None = None) -> dict:
    """Busca uma lista pelo ID, verificando ownership.

    `profile_id` opcional (fallback pra token antigo sem essa claim)."""
    query = (
        supabase.table("product_lists")
        .select("*")
        .eq("id", product_list_id)
        .eq("user_id", user_id)
    )
    if profile_id:
        query = query.eq("profile_id", profile_id)
    result = query.single().execute()
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


def _sync_list_products(
    user_id: int, list_id: int, product_ids: list[int], profile_id: str | None = None
) -> None:
    """Sincroniza `product_lists_products` com `product_ids`.

    Só associa produtos pertencentes ao usuário (e ao perfil ativo, quando
    houver — evita IDOR via produto de outro usuário ou de outro perfil). O client Supabase REST não expõe transação (mesma
    limitação dos outros endpoints deste router) — insert e delete são duas
    chamadas separadas, não atômicas.
    """
    owned_ids: set[int] = set()
    if product_ids:
        owned_result = (
            scope_owner(supabase.table("products").select("id"), user_id, profile_id)
            .in_("id", product_ids)
            .execute()
        )
        owned_ids = {row["id"] for row in (owned_result.data or [])}

    current_result = (
        supabase.table("product_lists_products")
        .select("product_id")
        .eq("product_list_id", list_id)
        .execute()
    )
    current_ids = {row["product_id"] for row in (current_result.data or [])}

    to_add = owned_ids - current_ids
    to_remove = current_ids - owned_ids

    if to_add:
        supabase.table("product_lists_products").insert(
            [{"product_list_id": list_id, "product_id": pid} for pid in to_add]
        ).execute()

    if to_remove:
        (
            supabase.table("product_lists_products")
            .delete()
            .eq("product_list_id", list_id)
            .in_("product_id", list(to_remove))
            .execute()
        )


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_product_lists(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    cursor: str | None = Query(None, description="Cursor de paginação"),
    limit: int = Query(20, ge=1, le=100, description="Tamanho da página"),
):
    """Lista listas de produtos com paginação por cursor."""
    query = supabase.table("product_lists").select("*").eq("user_id", user_id)
    if profile_id:
        query = query.eq("profile_id", profile_id)
    query = query.order("created_at", desc=True).limit(limit)
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


@router.post("")
async def create_product_list(
    body: ProductListCreate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Cria uma nova lista de produtos."""
    data = {"user_id": user_id, "name": body.name}
    if profile_id:
        data["profile_id"] = profile_id
    result = supabase.table("product_lists").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar lista")
    return result.data[0]


@router.get("/{product_list_id}")
async def get_product_list(
    product_list_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Retorna uma lista específica com seus produtos."""
    list_data = _get_list(user_id, product_list_id, profile_id)
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
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Atualiza o nome de uma lista."""
    _get_list(user_id, product_list_id, profile_id)  # ownership check

    update_query = (
        supabase.table("product_lists")
        .update({"name": body.name})
        .eq("id", product_list_id)
        .eq("user_id", user_id)
    )
    if profile_id:
        update_query = update_query.eq("profile_id", profile_id)
    result = update_query.single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lista não encontrada")

    if body.product_ids is not None:
        _sync_list_products(user_id, product_list_id, body.product_ids, profile_id)

    return result.data


@router.delete("/{product_list_id}")
async def delete_product_list(
    product_list_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Remove uma lista de produtos."""
    before = _get_list(user_id, product_list_id, profile_id)  # ownership check

    delete_query = (
        supabase.table("product_lists")
        .delete()
        .eq("id", product_list_id)
        .eq("user_id", user_id)
    )
    if profile_id:
        delete_query = delete_query.eq("profile_id", profile_id)
    result = delete_query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lista não encontrada")

    record_audit_event(
        entity="product_list",
        entity_id=str(product_list_id),
        user_id=str(user_id),
        action="product_list_deleted",
        old_value=before,
        new_value=None,
        profile_id=profile_id,
    )

    return {"msg": "Lista removida"}
