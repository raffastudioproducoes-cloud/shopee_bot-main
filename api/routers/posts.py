"""
Posts Router — API Python (FastAPI)

CRUD de posts + copywriter IA + agendamento/publicação. Escopo desta
fase (migração React): post único (sem encadeamento em thread) e sem
upload de mídia — o Flask (`web/routes/posts.py`) ainda cobre thread
multi-parte e mídia. Agendamento/publicação passam pelo bridge interno
(`api/internal_client.py` -> `web/routes/internal.py`) porque o
APScheduler só roda de verdade no processo Flask — ver docstring de
internal_client.py e Fase 8 em docs/ROADMAP_MIGRACAO.md.

Publicação de verdade hoje só existe pra Threads (`func="bot_post"`,
`scheduler/bot_post.py`) — as outras 5 redes têm credencial mas nenhum
wrapper de publicação ligado ao scheduler ainda.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, model_validator

from .auth import get_current_user_id
from ..database import supabase
from ..internal_client import (
    create_scheduler_job,
    remove_scheduler_job,
    run_scheduler_job,
    InternalApiError,
)

router = APIRouter(prefix="/posts", tags=["posts"])


# ── Schemas ──────────────────────────────────────────────────────────────────────

class PostSchedule(BaseModel):
    trigger: Literal["cron", "date"]
    time: str | None = None  # "HH:MM", obrigatório se trigger=cron
    day_of_week: int | None = None  # 0-6, obrigatório se trigger=cron
    start_date: str | None = None  # ISO 8601, opcional em cron
    run_date: str | None = None  # ISO 8601, obrigatório se trigger=date

    @model_validator(mode="after")
    def _check_required_fields(self):
        if self.trigger == "cron" and (self.time is None or self.day_of_week is None):
            raise ValueError("time e day_of_week são obrigatórios para trigger 'cron'")
        if self.trigger == "date" and self.run_date is None:
            raise ValueError("run_date é obrigatório para trigger 'date'")
        return self


class PostCreate(BaseModel):
    text: str
    product_ids: list[int] = []
    schedule: PostSchedule


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


def _get_scheduler_job(post_id: int) -> dict | None:
    result = (
        supabase.table("schedulers").select("id")
        .eq("post_id", post_id).maybe_single().execute()
    )
    return result.data if result else None


def _delete_post_cascade(post_id: int) -> None:
    """Apaga post + associações (produtos). Usado tanto no DELETE quanto
    pra desfazer a criação se o agendamento falhar (ver create_post)."""
    supabase.table("posts_products").delete().eq("post_id", post_id).execute()
    supabase.table("posts").delete().eq("id", post_id).execute()


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
        job = _get_scheduler_job(item["id"])
        posts.append({
            **item,
            "products": _get_post_products(item["id"]),
            "scheduled": job is not None,
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
    """Cria um post (sem thread, sem mídia — ver docstring do módulo) e
    agenda a publicação. Se o agendamento falhar, desfaz a criação —
    melhor não criar do que criar um post que nunca vai publicar."""
    result = (
        supabase.table("posts")
        .insert({"user_id": user_id, "text": body.text, "post_id": None})
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar post")

    post = result.data[0]
    _set_post_products(post["id"], body.product_ids)

    try:
        await create_scheduler_job(
            user_id=user_id,
            post_id=post["id"],
            func="bot_post",
            trigger=body.schedule.trigger,
            time=body.schedule.time,
            day_of_week=body.schedule.day_of_week,
            start_date=body.schedule.start_date,
            run_date=body.schedule.run_date,
        )
    except InternalApiError:
        _delete_post_cascade(post["id"])
        raise HTTPException(
            status_code=502,
            detail="Não foi possível agendar a publicação agora. Post não foi criado.",
        )

    return {**post, "products": _get_post_products(post["id"]), "scheduled": True}


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
):
    post = _get_post(user_id, post_id)
    job = _get_scheduler_job(post_id)
    return {**post, "products": _get_post_products(post_id), "scheduled": job is not None}


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


@router.post("/{post_id}/publish")
async def publish_post_now(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Força a publicação imediata de um post já agendado."""
    _get_post(user_id, post_id)  # ownership check
    job = _get_scheduler_job(post_id)
    if not job:
        raise HTTPException(status_code=409, detail="Post não tem agendamento — nada pra publicar")

    try:
        await run_scheduler_job(job["id"])
    except InternalApiError:
        raise HTTPException(status_code=502, detail="Não foi possível publicar agora. Tente novamente.")

    return {"msg": "Publicação disparada"}


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
):
    _get_post(user_id, post_id)  # ownership check

    job = _get_scheduler_job(post_id)
    if job:
        try:
            await remove_scheduler_job(user_id, job["id"])
        except InternalApiError:
            raise HTTPException(
                status_code=502,
                detail="Não foi possível remover o agendamento agora. Post não foi removido.",
            )

    _delete_post_cascade(post_id)
    return {"msg": "Post removido"}
