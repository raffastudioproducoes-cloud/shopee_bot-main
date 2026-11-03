"""Prévia e rascunhos inertes de campanhas; nunca ativa disparos.

Execução futura exige políticas de rede, idempotência e congelamento T-30.
"""
from datetime import date, time, datetime, timezone, timedelta
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field, field_validator

from ..campaign_schedule import plan_campaign_slots
from ..campaign_policy import (
    load_campaign_policy, validate_campaign_plan_schedule, require_campaign_access,
    campaign_limits_response, validate_campaign_network_volume,
)
from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .lists import _get_list, _get_list_products
from ..database import supabase
from ..storage_capacity import storage_upload_reservation
from .posts import _read_media_content, _sanitize_upload, MEDIA_DRAFT_BUCKET
from ..profiles import scope_owner
from urllib.parse import urlsplit
from typing import Literal
from uuid import UUID


router = APIRouter(prefix="/campaigns", tags=["campaigns"])
logger = logging.getLogger(__name__)
MAX_CAMPAIGN_MEDIA_PER_PRODUCT = 10



class CampaignPreviewRequest(BaseModel):
    list_id: int = Field(gt=0)
    item_ids: list[int] = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start_time: time
    end_time: time
    posts_per_day: int = Field(ge=1, le=15)


def validate_campaign_list_items(requested_ids: list[int], owned_list_ids: list[int]) -> None:
    """Somente uma permutação exata da lista; impede IDs de outras listas/duplicatas."""
    if (
        len(requested_ids) != len(owned_list_ids)
        or len(set(requested_ids)) != len(requested_ids)
        or set(requested_ids) != set(owned_list_ids)
    ):
        raise ValueError("A ordem selecionada precisa conter exatamente os produtos da lista, sem repetições.")


@router.get("/limits")
async def get_campaign_limits(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Elegibilidade comercial, sem afirmar execução ou consumo inexistentes."""
    profile_id = _draft_profile(profile_id)
    return campaign_limits_response(load_campaign_policy(user_id, profile_id), profile_id)


@router.post("/preview")
async def preview_campaign(
    body: CampaignPreviewRequest,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Prévia do planejamento. Não cria, agenda ou publica posts."""
    if not profile_id:
        raise HTTPException(status_code=400, detail="Perfil ativo obrigatório.")
    policy = load_campaign_policy(user_id, profile_id)
    validate_campaign_plan_schedule(policy, body)
    product_list = _get_list(user_id, body.list_id, profile_id)
    products = _get_list_products(product_list["id"])
    try:
        validate_campaign_list_items(body.item_ids, [int(p["id"]) for p in products])
        slots = plan_campaign_slots(
            start_date=body.start_date,
            end_date=body.end_date,
            weekdays=body.weekdays,
            start_time=body.start_time,
            end_time=body.end_time,
            posts_per_day=body.posts_per_day,
            item_ids=body.item_ids,
            timezone="America/Sao_Paulo",
        )
        if len(slots) > 2000:
            raise ValueError("A prévia excede 2.000 horários. Reduza a quantidade por dia ou os dias selecionados.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    uncovered = body.item_ids[len(slots):] if len(slots) < len(body.item_ids) else []
    return {
        "list_id": product_list["id"],
        "list_name": product_list["name"],
        "product_count": len(body.item_ids),
        "slot_count": len(slots),
        "uncovered_item_ids": uncovered,
        "uncovered_count": len(uncovered),
        "truncated": len(slots) > 60,
        "slots": [
            {
                "sequence": slot.occurrence_index + 1,
                "product_id": slot.item_id,
                "scheduled_local": slot.local_at.isoformat(),
                "scheduled_utc": slot.utc_at.isoformat(),
            }
            for slot in slots[:60]
        ],
        "timezone": "America/Sao_Paulo",
        "activated": False,
        "network_quota_validated": False,
        "message": "Prévia somente. Nenhum post foi criado, agendado ou publicado.",
    }


# F3A: rascunhos somente. Não materializa posts, jobs ou mídias.
Network = Literal["threads", "x", "facebook", "instagram", "tiktok"]


class CampaignDraftItem(BaseModel):
    product_id: int = Field(gt=0)
    title: str = Field(max_length=300)
    copy: str = Field(max_length=10000)
    affiliate_link: str = Field(default="", max_length=2048)
    networks: list[Network] = Field(default_factory=list, max_length=5)
    network_copies: dict[Network, str] = Field(default_factory=dict)
    use_shopee_image: bool = True

    @field_validator("affiliate_link")
    @classmethod
    def valid_link(cls, v):
        if v:
            u = urlsplit(v)
            if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password:
                raise ValueError("Link de afiliado deve ser HTTP(S) válido.")
        return v

    @field_validator("networks")
    @classmethod
    def unique_networks(cls, v):
        if len(v) != len(set(v)):
            raise ValueError("Não repita redes sociais.")
        return v

    @field_validator("network_copies")
    @classmethod
    def bounded_copies(cls, v):
        if any(len(t) > 10000 for t in v.values()):
            raise ValueError("Texto por rede excede o limite.")
        return v


class CampaignDraftSave(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value):
        name = value.strip()
        if not name:
            raise ValueError("Dê um nome para a campanha.")
        return name

    list_id: int = Field(gt=0)
    items: list[CampaignDraftItem] = Field(min_length=1, max_length=100)
    schedule: CampaignPreviewRequest | None = None


class CampaignDraftUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value):
        name = value.strip()
        if not name:
            raise ValueError("Dê um nome para a campanha.")
        return name

    expected_revision: int = Field(ge=1)
    items: list[CampaignDraftItem] = Field(min_length=1, max_length=100)
    schedule: CampaignPreviewRequest | None = None


def validate_campaign_draft_items(items: list, owned_ids: list[int]) -> None:
    ids = [int(item["product_id"] if isinstance(item, dict) else item.product_id) for item in items]
    validate_campaign_list_items(ids, owned_ids)


def validate_campaign_draft_schedule(
    schedule: CampaignPreviewRequest | None, list_id: int | None, item_ids: list[int],
) -> None:
    """A agenda, quando presente, deve descrever o mesmo snapshot e ser válida."""
    if schedule is None:
        return
    if list_id is None or schedule.list_id != list_id:
        raise ValueError("O planejamento precisa corresponder à lista da campanha.")
    if schedule.item_ids != item_ids:
        raise ValueError("O planejamento precisa usar a ordem exata dos produtos preparados.")
    plan_campaign_slots(
        start_date=schedule.start_date, end_date=schedule.end_date,
        weekdays=schedule.weekdays, start_time=schedule.start_time,
        end_time=schedule.end_time, posts_per_day=schedule.posts_per_day,
        item_ids=schedule.item_ids, timezone="America/Sao_Paulo",
    )


def _draft_profile(profile_id):
    if not profile_id:
        raise HTTPException(status_code=400, detail="Perfil ativo obrigatório.")
    return profile_id


@router.post("/drafts", status_code=201)
async def create_campaign_draft(
    body: CampaignDraftSave,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id = _draft_profile(profile_id)
    policy = load_campaign_policy(user_id, profile_id)
    validate_campaign_plan_schedule(policy, body.schedule)
    source = _get_list(user_id, body.list_id, profile_id)
    products = _get_list_products(source["id"])
    try:
        validate_campaign_draft_items(body.items, [int(p["id"]) for p in products])
        validate_campaign_draft_schedule(body.schedule, body.list_id, [p.product_id for p in body.items])
        validate_campaign_network_volume(policy, body.schedule, body.items)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    by_id = {int(p["id"]): p for p in products}
    items = []
    for item in body.items:
        saved = item.model_dump(mode="json")
        saved["source_image"] = by_id[item.product_id].get("image")
        saved["use_shopee_image"] = bool(saved["source_image"]) and item.use_shopee_image
        items.append(saved)
    result = supabase.table("campaign_drafts").insert({
        "user_id": user_id, "profile_id": profile_id,
        "source_list_id": body.list_id, "source_list_name": source["name"],
        "campaign_name": body.name,
        "items": items,
        "schedule": body.schedule.model_dump(mode="json") if body.schedule else None,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Não foi possível salvar a campanha.")
    return result.data[0]


@router.get("/drafts")
async def list_campaign_drafts(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    result = (scope_owner(supabase.table("campaign_drafts").select("*"),
                          user_id, _draft_profile(profile_id))
              .order("updated_at", desc=True).limit(30).execute())
    return {"data": result.data or []}


def _get_owned_campaign(draft_id: UUID, user_id: int, profile_id: str):
    result = (scope_owner(supabase.table("campaign_drafts").select("*")
              .eq("id", str(draft_id)), user_id, profile_id)
              .maybe_single().execute())
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Rascunho de campanha não encontrado.")
    return result.data


@router.get("/drafts/{draft_id}")
async def get_campaign_draft(
    draft_id: UUID,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    return _get_owned_campaign(draft_id, user_id, _draft_profile(profile_id))


@router.get("/drafts/{draft_id}/preflight")
async def preflight_campaign_draft(
    draft_id: UUID, expected_revision: int = Query(..., ge=1),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Leitura parcial: não reserva vaga nem valida prontidão para publicar."""
    profile_id = _draft_profile(profile_id)
    policy = load_campaign_policy(user_id, profile_id)
    require_campaign_access(policy)
    draft = _get_owned_campaign(draft_id, user_id, profile_id)
    if draft.get("status") != "draft" or draft.get("revision") != expected_revision:
        raise HTTPException(status_code=409, detail="Rascunho alterado; atualize a revisão.")
    try:
        items = [CampaignDraftItem.model_validate(x) for x in draft["items"]]
        if not items or any(not item.networks for item in items):
            raise ValueError("Cada produto precisa de ao menos uma rede.")
        schedule = CampaignPreviewRequest.model_validate(draft["schedule"])
        validate_campaign_draft_schedule(
            schedule, draft.get("source_list_id"), [item.product_id for item in items],
        )
        validate_campaign_plan_schedule(policy, schedule)
        validate_campaign_network_volume(policy, schedule, items)
        slots = plan_campaign_slots(
            start_date=schedule.start_date, end_date=schedule.end_date,
            weekdays=schedule.weekdays, start_time=schedule.start_time,
            end_time=schedule.end_time, posts_per_day=schedule.posts_per_day,
            item_ids=schedule.item_ids, timezone="America/Sao_Paulo",
        )
        if not slots or any(slot.utc_at <= datetime.now(timezone.utc) for slot in slots):
            raise ValueError("Os horários precisam estar no futuro.")
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Planejamento de campanha inválido.") from None
    return {
        "status": "preflight_only", "reservation_available": False,
        "reserved": False, "activated": False, "checks_complete": False,
        "occurrence_count": len(slots),
        "planned_utc": [slot.utc_at.strftime("%Y-%m-%dT%H:%M:%SZ") for slot in slots],
        "pending_checks": ["quota_atomica", "retencao_midia", "oauth_redes", "dispatch"],
    }


@router.put("/drafts/{draft_id}")
async def update_campaign_draft(
    draft_id: UUID, body: CampaignDraftUpdate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id = _draft_profile(profile_id)
    old = _get_owned_campaign(draft_id, user_id, profile_id)
    policy = load_campaign_policy(user_id, profile_id)
    validate_campaign_plan_schedule(policy, body.schedule)
    if old.get("status") != "draft" or int(old["revision"]) != body.expected_revision:
        raise HTTPException(status_code=409, detail="Rascunho mudou. Recarregue antes de salvar.")
    old_items = {int(p["product_id"]): p for p in old["items"]}
    try:
        validate_campaign_draft_items(body.items, list(old_items))
        validate_campaign_draft_schedule(body.schedule, old.get("source_list_id"), [p.product_id for p in body.items])
        validate_campaign_network_volume(policy, body.schedule, body.items)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    items = []
    for item in body.items:
        saved = item.model_dump(mode="json")
        saved["source_image"] = old_items[item.product_id].get("source_image")
        saved["use_shopee_image"] = bool(saved["source_image"]) and item.use_shopee_image
        items.append(saved)
    update = {"items": items, "campaign_name": body.name,
              "schedule": body.schedule.model_dump(mode="json") if body.schedule else None,
              "revision": body.expected_revision + 1,
              "updated_at": datetime.now(timezone.utc).isoformat()}
    result = (scope_owner(supabase.table("campaign_drafts").update(update)
              .eq("id", str(draft_id)).eq("status", "draft")
              .eq("revision", body.expected_revision), user_id, profile_id).execute())
    if not result.data:
        raise HTTPException(status_code=409, detail="Rascunho modificado por outra sessão.")
    return result.data[0]


@router.delete("/drafts/{draft_id}", status_code=204)
async def delete_campaign_draft(
    draft_id: UUID,
    expected_revision: int = Query(ge=1),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Exclui apenas rascunho próprio. Apaga mídia privada ANTES da cascata SQL.

    Não toca em listas-fonte, posts nem jobs. Falha fechada se a limpeza do
    Storage não puder ser confirmada; cliente pode tentar novamente.
    """
    profile_id = _draft_profile(profile_id)
    draft = _get_owned_campaign(draft_id, user_id, profile_id)
    if draft.get("status") != "draft" or int(draft["revision"]) != expected_revision:
        raise HTTPException(status_code=409, detail="Rascunho alterado. Recarregue antes de excluir.")

    media = (scope_owner(supabase.table("campaign_draft_media")
             .select("id, storage_bucket, storage_key, status")
             .eq("campaign_id", str(draft_id)).limit(1001),
             user_id, profile_id).execute()).data or []
    if len(media) > 1000 or any(row["status"] == "uploading" for row in media):
        raise HTTPException(status_code=409, detail="Há arquivos em processamento. Tente excluir depois.")
    keys = []
    for row in media:
        key = row.get("storage_key")
        if row.get("storage_bucket") != MEDIA_DRAFT_BUCKET or not isinstance(key, str) or not key.startswith(
            f"campaigns/{user_id}/{profile_id}/{draft_id}/"
        ):
            raise HTTPException(status_code=409, detail="Referência de anexo inválida. Nada foi excluído.")
        keys.append(key)
    try:
        for offset in range(0, len(keys), 100):
            supabase.storage.from_(MEDIA_DRAFT_BUCKET).remove(keys[offset:offset + 100])
    except Exception:
        logger.warning("Falha ao limpar anexos antes da exclusão do rascunho", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao remover arquivos. O rascunho foi preservado.") from None

    # Se algum upload entrou no intervalo de limpeza, não apagar a campanha
    # nem perder suas referências. Repetir a operação após encerrar o upload.
    current_media = (scope_owner(supabase.table("campaign_draft_media")
                     .select("id").eq("campaign_id", str(draft_id)).limit(1001),
                     user_id, profile_id).execute()).data or []
    if {row["id"] for row in current_media} != {row["id"] for row in media}:
        raise HTTPException(status_code=409, detail="Os anexos mudaram. Atualize e tente excluir novamente.")

    removed = (scope_owner(supabase.table("campaign_drafts").delete()
               .eq("id", str(draft_id)).eq("status", "draft")
               .eq("revision", expected_revision), user_id, profile_id).execute())
    if not removed.data:
        raise HTTPException(status_code=409, detail="Rascunho alterado. Recarregue antes de excluir.")
    return None


# F3B: anexos duráveis por produto, independentes do TTL das publicações únicas.
# Não materializa posts, não mexe no scheduler e não oferece URL pública.
def _campaign_media_response(row: dict) -> dict:
    return {key: row.get(key) for key in
            ("id", "product_id", "slot", "file_name", "media_type",
             "size_bytes", "status", "created_at")}


def _ready_campaign_media(draft_id: UUID, user_id: int, profile_id: str):
    return (scope_owner(supabase.table("campaign_draft_media")
             .select("id, product_id, slot, file_name, media_type, size_bytes, status, created_at")
             .eq("campaign_id", str(draft_id)).eq("status", "ready"),
             user_id, profile_id)
            .order("product_id").order("slot").execute()).data or []


def _assert_draft_product(draft: dict, product_id: int) -> None:
    if draft.get("status") != "draft" or not any(
        int(item["product_id"]) == product_id for item in draft["items"]
    ):
        raise HTTPException(status_code=404, detail="Produto indisponível neste rascunho.")


@router.get("/drafts/{draft_id}/media")
async def list_campaign_media(
    draft_id: UUID,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id = _draft_profile(profile_id)
    _get_owned_campaign(draft_id, user_id, profile_id)
    return {"data": [_campaign_media_response(row) for row in
                     _ready_campaign_media(draft_id, user_id, profile_id)]}


def _cleanup_abandoned_campaign_media(draft_id: UUID, user_id: int, profile_id: str) -> None:
    """Na próxima inclusão, recolhe somente uploads incompletos >2h; NUNCA 'ready'."""
    stale_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    rows = (scope_owner(supabase.table("campaign_draft_media")
            .select("id, storage_bucket, storage_key").eq("campaign_id", str(draft_id))
            .in_("status", ["uploading", "delete_failed"])
            .lt("created_at", stale_at).limit(20), user_id, profile_id).execute()).data or []
    for row in rows:
        try:
            if row["storage_bucket"] != MEDIA_DRAFT_BUCKET or not row["storage_key"].startswith(
                f"campaigns/{user_id}/{profile_id}/{draft_id}/"
            ):
                logger.warning("Prefixo inesperado em mídia de campanha abandonada")
                continue
            supabase.storage.from_(MEDIA_DRAFT_BUCKET).remove([row["storage_key"]])
            (scope_owner(supabase.table("campaign_draft_media").delete()
                         .eq("id", row["id"]).in_("status", ["uploading", "delete_failed"]),
                         user_id, profile_id).execute())
        except Exception:
            logger.warning("Não foi possível recolher upload de campanha abandonado", exc_info=True)


@router.post("/drafts/{draft_id}/items/{product_id}/media", status_code=201)
async def upload_campaign_media(
    draft_id: UUID, product_id: int, file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id = _draft_profile(profile_id)
    draft = _get_owned_campaign(draft_id, user_id, profile_id)
    _assert_draft_product(draft, product_id)
    require_campaign_access(load_campaign_policy(user_id, profile_id))
    _cleanup_abandoned_campaign_media(draft_id, user_id, profile_id)

    # Sanitizar com a mesma pipeline da publicação única; nada é publicado.
    raw = await _read_media_content(file)
    media = await _sanitize_upload(file, raw)
    existing = (scope_owner(supabase.table("campaign_draft_media")
                 .select("slot").eq("campaign_id", str(draft_id))
                 .eq("product_id", product_id), user_id, profile_id).execute()).data or []
    used = {int(row["slot"]) for row in existing}
    slot = next((number for number in range(MAX_CAMPAIGN_MEDIA_PER_PRODUCT)
                 if number not in used), None)
    if slot is None:
        raise HTTPException(status_code=422, detail="Máximo de 10 arquivos por produto.")

    media_id = str(uuid.uuid4())
    key = f"campaigns/{user_id}/{profile_id}/{draft_id}/{product_id}/{media_id}{media.extension}"
    record = {
        "id": media_id, "campaign_id": str(draft_id), "product_id": product_id,
        "user_id": user_id, "profile_id": profile_id, "slot": slot,
        "storage_bucket": MEDIA_DRAFT_BUCKET, "storage_key": key,
        "file_name": media.safe_filename, "mime_type": media.mime_type,
        "media_type": media.media_type, "size_bytes": len(media.content),
        "status": "uploading",
    }
    try:
        inserted = supabase.table("campaign_draft_media").insert(record).execute()
        if not inserted.data:
            raise HTTPException(status_code=409, detail="Não foi possível reservar um espaço. Tente novamente.")
    except HTTPException:
        raise
    except Exception:
        logger.info("Slot de mídia concorrente ou indisponível", exc_info=True)
        raise HTTPException(status_code=409, detail="O arquivo não pôde ser reservado. Atualize e tente novamente.")

    uploaded = False
    try:
        with storage_upload_reservation(len(media.content)):
            supabase.storage.from_(MEDIA_DRAFT_BUCKET).upload(
                key, media.content, {"content-type": media.mime_type, "upsert": "false"})
            uploaded = True
        saved = (scope_owner(supabase.table("campaign_draft_media")
                 .update({"status": "ready"}).eq("id", media_id)
                 .eq("status", "uploading"), user_id, profile_id).execute())
        if not saved.data:
            raise RuntimeError("O banco não confirmou a mídia.")
        return _campaign_media_response(saved.data[0])
    except Exception:
        logger.warning("Falha ao persistir anexo da campanha", exc_info=True)
        cleaned = not uploaded
        if uploaded:
            try:
                supabase.storage.from_(MEDIA_DRAFT_BUCKET).remove([key])
                cleaned = True
            except Exception:
                logger.warning("Falha no rollback do anexo; registro será recuperável", exc_info=True)
        if cleaned:
            (scope_owner(supabase.table("campaign_draft_media").delete().eq("id", media_id)
                         .eq("status", "uploading"), user_id, profile_id).execute())
        else:
            (scope_owner(supabase.table("campaign_draft_media").update({"status": "delete_failed"})
                         .eq("id", media_id), user_id, profile_id).execute())
        raise HTTPException(status_code=502, detail="Falha ao armazenar o arquivo. Tente novamente.") from None


@router.delete("/drafts/{draft_id}/media/{media_id}", status_code=204)
async def delete_campaign_media(
    draft_id: UUID, media_id: UUID,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id = _draft_profile(profile_id)
    draft = _get_owned_campaign(draft_id, user_id, profile_id)
    if draft.get("status") != "draft":
        raise HTTPException(status_code=409, detail="Campanha não editável.")
    result = (scope_owner(supabase.table("campaign_draft_media").select(
        "id, storage_bucket, storage_key, status").eq("campaign_id", str(draft_id))
        .eq("id", str(media_id)).eq("status", "ready"),
        user_id, profile_id).maybe_single().execute())
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    stored = result.data
    key = stored["storage_key"]
    if stored["storage_bucket"] != MEDIA_DRAFT_BUCKET or not key.startswith(
        f"campaigns/{user_id}/{profile_id}/{draft_id}/"
    ):
        raise HTTPException(status_code=409, detail="Referência de mídia inválida.")
    try:
        supabase.storage.from_(MEDIA_DRAFT_BUCKET).remove([key])
    except Exception:
        logger.warning("Falha ao apagar anexo da campanha", exc_info=True)
        raise HTTPException(status_code=502, detail="Não foi possível excluir o arquivo agora.") from None
    (scope_owner(supabase.table("campaign_draft_media").delete()
                 .eq("campaign_id", str(draft_id)).eq("id", str(media_id))
                 .eq("status", "ready"), user_id, profile_id).execute())
    return None
