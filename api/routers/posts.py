"""
Posts Router — API Python (FastAPI)

CRUD de posts (thread multi-parte) + copywriter IA + agendamento/
publicação. Agendamento/publicação passam pelo bridge interno
(`api/internal_client.py` -> `web/routes/internal.py`) porque o
APScheduler só roda de verdade no processo Flask — ver docstring de
internal_client.py e Fase 8 em docs/ROADMAP_MIGRACAO.md.

Escopo simplificado: sem upload de mídia (o Flask ainda cobre isso —
sobe pra `web/media/<post_id>/`, cifra pro Cloudinary na publicação).

Modelo de thread: cada parte é uma linha em `posts`; a primeira
("head", a única retornada por list_posts) tem `post_id IS NULL`; cada
parte seguinte tem `post_id` apontando pra parte ANTERIOR (lista
encadeada por trás pra frente, não por índice). Produtos e agendamento
sempre grudam na head. Publicação de verdade hoje só existe pra Threads
(`func="bot_post"`, `scheduler/bot_post.py`) — as outras 5 redes têm
credencial mas nenhum wrapper de publicação ligado ao scheduler ainda.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, model_validator, field_validator

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
    texts: list[str]  # 1 item = post único; 2+ = thread encadeada
    product_ids: list[int] = []
    schedule: PostSchedule

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, v):
        if not v or not any(t.strip() for t in v):
            raise ValueError("texts precisa ter ao menos um item com texto")
        return v


class PostUpdate(BaseModel):
    texts: list[str]
    product_ids: list[int] = []

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, v):
        if not v or not any(t.strip() for t in v):
            raise ValueError("texts precisa ter ao menos um item com texto")
        return v


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


def _get_thread_chain(head_id: int) -> list[dict]:
    """Head primeiro, depois cada parte seguinte (post_id aponta pra
    parte ANTERIOR — ver docstring do módulo). Bounded por MAX_PARTS
    pra nunca entrar em loop infinito se o dado estiver corrompido."""
    MAX_PARTS = 50
    chain = [_get_post_by_id_only(head_id)]
    current_id = head_id
    for _ in range(MAX_PARTS):
        next_result = (
            supabase.table("posts").select("*")
            .eq("post_id", current_id).maybe_single().execute()
        )
        if not next_result or not next_result.data:
            break
        chain.append(next_result.data)
        current_id = next_result.data["id"]
    return chain


def _get_post_by_id_only(post_id: int) -> dict:
    result = supabase.table("posts").select("*").eq("id", post_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")
    return result.data


def _create_thread(user_id: int, texts: list[str]) -> dict:
    """Insere a thread inteira, encadeando post_id. Retorna a head."""
    parent_id = None
    head = None
    for text in texts:
        result = (
            supabase.table("posts")
            .insert({"user_id": user_id, "text": text, "post_id": parent_id})
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Falha ao criar post")
        row = result.data[0]
        if head is None:
            head = row
        parent_id = row["id"]
    return head


def _delete_thread_cascade(head_id: int) -> None:
    """Apaga a thread inteira (head + partes) + associações de produto.
    Usado no DELETE e pra desfazer a criação se o agendamento falhar."""
    chain = _get_thread_chain(head_id)
    supabase.table("posts_products").delete().eq("post_id", head_id).execute()
    # apaga de trás pra frente: cada parte tem post_id apontando pra
    # anterior, então a anterior não pode sumir primeiro (FK)
    for row in reversed(chain):
        supabase.table("posts").delete().eq("id", row["id"]).execute()


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
        chain = _get_thread_chain(item["id"])
        posts.append({
            **item,
            "texts": [row["text"] for row in chain],
            "products": _get_post_products(item["id"]),
            "scheduled": job is not None,
            "parts_count": len(chain),
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
    """Cria a thread (1+ partes, ver docstring do módulo) e agenda a
    publicação. Se o agendamento falhar, desfaz a criação inteira —
    melhor não criar do que criar um post que nunca vai publicar."""
    head = _create_thread(user_id, body.texts)
    _set_post_products(head["id"], body.product_ids)

    try:
        await create_scheduler_job(
            user_id=user_id,
            post_id=head["id"],
            func="bot_post",
            trigger=body.schedule.trigger,
            time=body.schedule.time,
            day_of_week=body.schedule.day_of_week,
            start_date=body.schedule.start_date,
            run_date=body.schedule.run_date,
        )
    except InternalApiError:
        _delete_thread_cascade(head["id"])
        raise HTTPException(
            status_code=502,
            detail="Não foi possível agendar a publicação agora. Post não foi criado.",
        )

    return {
        **head,
        "texts": body.texts,
        "products": _get_post_products(head["id"]),
        "scheduled": True,
    }


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
):
    post = _get_post(user_id, post_id)
    job = _get_scheduler_job(post_id)
    chain = _get_thread_chain(post_id)
    return {
        **post,
        "texts": [row["text"] for row in chain],
        "products": _get_post_products(post_id),
        "scheduled": job is not None,
    }


@router.put("/{post_id}")
async def update_post(
    post_id: int,
    body: PostUpdate,
    user_id: int = Depends(get_current_user_id),
):
    """Atualiza a head (id fixo — mantém agendamento/produtos válidos)
    e substitui as partes seguintes (apaga e recria — simplificação:
    não tenta casar partes antigas com as novas por id)."""
    _get_post(user_id, post_id)  # ownership check

    chain = _get_thread_chain(post_id)
    for row in reversed(chain[1:]):
        supabase.table("posts").delete().eq("id", row["id"]).execute()

    result = (
        supabase.table("posts")
        .update({"text": body.texts[0]})
        .eq("id", post_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")

    parent_id = post_id
    for text in body.texts[1:]:
        row = (
            supabase.table("posts")
            .insert({"user_id": user_id, "text": text, "post_id": parent_id})
            .execute()
        )
        parent_id = row.data[0]["id"]

    _set_post_products(post_id, body.product_ids)
    return {
        **result.data[0],
        "texts": body.texts,
        "products": _get_post_products(post_id),
    }


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

    _delete_thread_cascade(post_id)
    return {"msg": "Post removido"}
