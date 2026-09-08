"""
Router placeholder — Posts (API Python)
CRUD de posts, agendamento e execução.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/posts", tags=["posts"])


class PostCreate(BaseModel):
    content: str
    scheduled_at: str | None = None
    product_id: str | None = None
    user_id: str


class PostUpdate(BaseModel):
    content: str | None = None
    scheduled_at: str | None = None


@router.get("/")
async def get_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    raise HTTPException(status_code=501, detail="Não implementado")


@router.get("/{post_id}")
async def get_post(post_id: str):
    raise HTTPException(status_code=501, detail="Não implementado")


@router.post("/", status_code=201)
async def create_post(post: PostCreate):
    raise HTTPException(status_code=501, detail="Não implementado")


@router.put("/{post_id}")
async def update_post(post_id: str, post: PostUpdate):
    raise HTTPException(status_code=501, detail="Não implementado")


@router.delete("/{post_id}")
async def delete_post(post_id: str):
    raise HTTPException(status_code=501, detail="Não implementado")


@router.post("/{post_id}/publish")
async def publish_post(post_id: str):
    raise HTTPException(status_code=501, detail="Não implementado")
