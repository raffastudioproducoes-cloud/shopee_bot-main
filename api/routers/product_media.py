"""Galeria permanente dos produtos, isolada por conta e no Storage privado existente.

Arquivos são sanitizados antes da gravação e respeitam a reserva global de espaço.
Não altera o upload de posts, as filas ou os publicadores.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from .auth import get_current_user_id
from ..database import supabase
from ..media_sanitizer import MediaSanitizerError, sanitize_media_upload
from ..profiles import scope_account
from ..storage_capacity import storage_upload_reservation
from ..video_processor import process_video_upload

router = APIRouter(prefix="/products", tags=["product-media"])
logger = logging.getLogger(__name__)

BUCKET = "post-media"  # bucket privado já usado por posts; não criar serviço ou bucket novo
MAX_UPLOAD = 50 * 1024 * 1024
LIMITS = {"IMAGE": 5, "VIDEO": 2}


def _require_owned_product(user_id: str, product_id: int) -> None:
    product = scope_account(
        supabase.table("products").select("id").eq("id", product_id), user_id,
    ).maybe_single().execute()
    if not product or not product.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado nesta conta.")


def _owned_asset(user_id: str, product_id: int, asset_id: str) -> dict[str, Any]:
    _require_owned_product(user_id, product_id)
    result = scope_account(
        supabase.table("product_media").select("*").eq("id", asset_id).eq("product_id", product_id),
        user_id,
    ).maybe_single().execute()
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Mídia não encontrada neste produto.")
    return result.data


def _signed_asset(row: dict[str, Any]) -> dict[str, Any]:
    try:
        signed = supabase.storage.from_(BUCKET).create_signed_url(row["storage_key"], 900)
        url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
        if not url:
            raise ValueError("signed URL unavailable")
    except Exception:
        logger.warning("Pré-visualização privada indisponível", exc_info=True)
        raise HTTPException(status_code=502, detail="Não foi possível abrir a mídia agora.") from None
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "media_type": row["media_type"],
        "file_name": row["file_name"],
        "size_bytes": row["size_bytes"],
        "slot": row["slot"],
        "preview_url": url,
    }


@router.get("/{product_id}/media")
async def list_product_media(product_id: int, user_id: str = Depends(get_current_user_id)):
    _require_owned_product(user_id, product_id)
    result = scope_account(
        supabase.table("product_media").select("*").eq("product_id", product_id).eq("status", "ready"),
        user_id,
    ).order("media_type").order("slot").execute()
    return {"items": [_signed_asset(row) for row in (result.data or [])]}


@router.post("/{product_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_product_media(
    product_id: int,
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
):
    """Até cinco imagens e dois vídeos por produto; valida magia e reprocessa mídia."""
    _require_owned_product(user_id, product_id)
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > MAX_UPLOAD:
            raise HTTPException(status_code=413, detail="Arquivo maior que 50 MB.")
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    try:
        media = await run_in_threadpool(
            sanitize_media_upload, content,
            filename=file.filename, content_type=file.content_type, max_bytes=MAX_UPLOAD,
        )
        if media.media_type == "VIDEO":
            video = await run_in_threadpool(process_video_upload, media.content, max_bytes=MAX_UPLOAD)
            media = replace(media, content=video)
    except MediaSanitizerError as exc:
        raise HTTPException(status_code=exc.status_code, detail=f"Mídia inválida: {exc}") from None

    if len(media.content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Arquivo processado maior que 50 MB.")

    existing = scope_account(
        supabase.table("product_media").select("slot").eq("product_id", product_id).eq("media_type", media.media_type),
        user_id,
    ).execute()
    occupied = {row["slot"] for row in (existing.data or [])}
    slot = next((i for i in range(1, LIMITS[media.media_type] + 1) if i not in occupied), None)
    if slot is None:
        raise HTTPException(status_code=409, detail="Limite de mídias deste tipo atingido.")

    asset_id = str(uuid.uuid4())
    key = f"products/{user_id}/{product_id}/{asset_id}{media.extension}"
    try:
        created = supabase.table("product_media").insert({
            "id": asset_id, "user_id": user_id, "product_id": product_id,
            "media_type": media.media_type, "slot": slot,
            "file_name": media.safe_filename, "mime_type": media.mime_type,
            "size_bytes": len(media.content), "storage_key": key, "status": "uploading",
        }).execute()
    except Exception as exc:
        if "23505" in str(exc) or "duplicate" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Outro upload está em andamento. Tente novamente.") from None
        raise
    if not created.data:
        raise HTTPException(status_code=500, detail="Não foi possível registrar a mídia.")

    uploaded = False
    try:
        with storage_upload_reservation(len(media.content)):
            supabase.storage.from_(BUCKET).upload(
                key, media.content, {"content-type": media.mime_type, "upsert": "false"}
            )
            uploaded = True
        updated = supabase.table("product_media").update({"status": "ready"}).eq("id", asset_id).eq("user_id", user_id).execute()
        if not updated.data:
            raise RuntimeError("media metadata was not confirmed")
    except Exception as exc:
        if uploaded:
            try:
                supabase.storage.from_(BUCKET).remove([key])
            except Exception:
                logger.warning("Arquivo órfão após falha de metadados %s", asset_id, exc_info=True)
        try:
            supabase.table("product_media").delete().eq("id", asset_id).eq("user_id", user_id).execute()
        except Exception:
            logger.warning("Falha ao limpar reserva de mídia %s", asset_id, exc_info=True)
        if isinstance(exc, HTTPException):
            raise
        logger.warning("Falha ao salvar mídia do produto", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao enviar mídia. Tente novamente.") from None
    return _signed_asset(updated.data[0])


@router.delete("/{product_id}/media/{asset_id}")
async def delete_product_media(
    product_id: int,
    asset_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
):
    row = _owned_asset(user_id, product_id, str(asset_id))
    try:
        supabase.storage.from_(BUCKET).remove([row["storage_key"]])
    except Exception:
        logger.warning("Falha ao remover mídia privada", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao remover arquivo. Tente novamente.") from None
    scope_account(
        supabase.table("product_media").delete().eq("id", str(asset_id)).eq("product_id", product_id), user_id,
    ).execute()
    return {"msg": "Mídia removida."}


def remove_product_media_files(user_id: str, product_id: int) -> None:
    """Remove objetos físicos antes do DELETE do produto. FK faz cascade dos metadados."""
    rows = scope_account(
        supabase.table("product_media").select("storage_key").eq("product_id", product_id), user_id,
    ).execute().data or []
    if rows:
        try:
            supabase.storage.from_(BUCKET).remove([row["storage_key"] for row in rows])
        except Exception:
            logger.warning("Exclusão de produto bloqueada: não foi possível limpar Storage", exc_info=True)
            raise HTTPException(status_code=502, detail="Não foi possível limpar as mídias do produto.")
