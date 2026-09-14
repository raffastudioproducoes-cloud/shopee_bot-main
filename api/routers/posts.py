"""
Posts Router — API Python (FastAPI)

CRUD de posts + copywriter IA. Escopo desta fase (migração React):
post único (sem encadeamento em thread) e sem upload de mídia — o
Flask (`web/routes/posts.py`) ainda cobre thread multi-parte, mídia e
publicação agendada/imediata (Cloudinary + Threads + APScheduler
compartilhado com o Flask). Ver docs/ROADMAP_MIGRACAO.md.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .auth import get_current_user_id
from ..database import supabase

router = APIRouter(prefix="/posts", tags=["posts"])


# ── Schemas ──────────────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    text: str
    product_ids: list[int] = []


class PostUpdate(BaseModel):
    text: str
    product_ids: list[int] = []


class GenerateCopyBody(BaseModel):
    product_id: int
    persona: str = "casual"


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _get_post(user_id: int, post_id: int) -> dict:
    result = (
        supabase.table("posts")
        .select("*")
        .eq("id", post_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")
    return result.data


def _get_post_products(post_id: int) -> list[dict]:
    result = (
        supabase.table("posts_products")
        .select("display_order, products(id, product_id, name, image, price_min, price_max, commission)")
        .eq("post_id", post_id)
        .order("display_order")
        .execute()
    )
    products: list[dict] = []
    for item in result.data or []:
        product = item.get("products")
        if product:
            products.append(product)
    return products


def _set_post_products(post_id: int, product_ids: list[int]) -> None:
    supabase.table("posts_products").delete().eq("post_id", post_id).execute()
    if product_ids:
        supabase.table("posts_products").insert([
            {"post_id": post_id, "product_id": pid, "display_order": i}
            for i, pid in enumerate(product_ids)
        ]).execute()


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.post("/generate-copy")
async def generate_copy(
    body: GenerateCopyBody,
    user_id: int = Depends(get_current_user_id),
):
    """Gera texto de post via IA (Gemini) para um produto, por persona."""
    from apis.llm import generate_product_copy

    product_result = (
        supabase.table("products")
        .select("*")
        .eq("id", body.product_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not product_result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    try:
        text = generate_product_copy(product_result.data, body.persona)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"text": text}


@router.get("/")
async def list_posts(
    user_id: int = Depends(get_current_user_id),
    cursor: str | None = Query(None, description="Cursor de paginação (created_at)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Lista posts únicos (post_id IS NULL — sem thread) com paginação por cursor."""
    query = (
        supabase.table("posts")
        .select("*")
        .eq("user_id", user_id)
        .is_("post_id", "null")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)

    result = query.execute()

    posts: list[dict] = []
    for item in result.data:
        posts.append({
            **item,
            "products": _get_post_products(item["id"]),
        })

    next_cursor = None
    if result.data and len(result.data) == limit:
        next_cursor = result.data[-1]["created_at"]

    return {"data": posts, "next_cursor": next_cursor}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostCreate,
    user_id: int = Depends(get_current_user_id),
):
    """Cria um post (sem thread, sem mídia — ver docstring do módulo)."""
    result = (
        supabase.table("posts")
        .insert({"user_id": user_id, "text": body.text, "post_id": None})
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar post")

    post = result.data[0]
    _set_post_products(post["id"], body.product_ids)
    return {**post, "products": _get_post_products(post["id"])}


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
):
    post = _get_post(user_id, post_id)
    return {**post, "products": _get_post_products(post_id)}


@router.put("/{post_id}")
async def update_post(
    post_id: int,
    body: PostUpdate,
    user_id: int = Depends(get_current_user_id),
):
    _get_post(user_id, post_id)  # ownership check

    result = (
        supabase.table("posts")
        .update({"text": body.text})
        .eq("id", post_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")

    _set_post_products(post_id, body.product_ids)
    return {**result.data[0], "products": _get_post_products(post_id)}


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
):
    _get_post(user_id, post_id)  # ownership check

    result = (
        supabase.table("posts")
        .delete()
        .eq("id", post_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")
    return {"msg": "Post removido"}
