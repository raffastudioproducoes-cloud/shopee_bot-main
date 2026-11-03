"""Prévia de campanhas por listas — leitura apenas, sem persistência/ativação.

A API só calcula horários para uma lista do usuário e perfil ativo;
a futura execução exige políticas de rede, idempotência e congelamento T-30.
"""
from datetime import date, time, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..campaign_schedule import plan_campaign_slots
from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .lists import _get_list, _get_list_products
from ..database import supabase
from ..profiles import scope_owner
from urllib.parse import urlsplit
from typing import Literal
from uuid import UUID


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignPreviewRequest(BaseModel):
    list_id: int = Field(gt=0)
    item_ids: list[int] = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start_time: time
    end_time: time
    interval_minutes: int = Field(ge=1, le=1440)


def validate_campaign_list_items(requested_ids: list[int], owned_list_ids: list[int]) -> None:
    """Somente uma permutação exata da lista; impede IDs de outras listas/duplicatas."""
    if (
        len(requested_ids) != len(owned_list_ids)
        or len(set(requested_ids)) != len(requested_ids)
        or set(requested_ids) != set(owned_list_ids)
    ):
        raise ValueError("A ordem selecionada precisa conter exatamente os produtos da lista, sem repetições.")


@router.post("/preview")
async def preview_campaign(
    body: CampaignPreviewRequest,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Prévia do planejamento. Não cria, agenda ou publica posts."""
    if not profile_id:
        raise HTTPException(status_code=400, detail="Perfil ativo obrigatório.")
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
            interval_minutes=body.interval_minutes,
            item_ids=body.item_ids,
            timezone="America/Sao_Paulo",
        )
        if len(slots) > 2000:
            raise ValueError("A prévia excede 2.000 horários. Aumente o intervalo ou reduza os dias.")
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
    list_id: int = Field(gt=0)
    items: list[CampaignDraftItem] = Field(min_length=1, max_length=100)
    schedule: CampaignPreviewRequest | None = None


class CampaignDraftUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    items: list[CampaignDraftItem] = Field(min_length=1, max_length=100)
    schedule: CampaignPreviewRequest | None = None


def validate_campaign_draft_items(items: list, owned_ids: list[int]) -> None:
    ids = [int(item["product_id"] if isinstance(item, dict) else item.product_id) for item in items]
    validate_campaign_list_items(ids, owned_ids)


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
    source = _get_list(user_id, body.list_id, profile_id)
    products = _get_list_products(source["id"])
    try:
        validate_campaign_draft_items(body.items, [int(p["id"]) for p in products])
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


@router.put("/drafts/{draft_id}")
async def update_campaign_draft(
    draft_id: UUID, body: CampaignDraftUpdate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    profile_id = _draft_profile(profile_id)
    old = _get_owned_campaign(draft_id, user_id, profile_id)
    if old.get("status") != "draft" or int(old["revision"]) != body.expected_revision:
        raise HTTPException(status_code=409, detail="Rascunho mudou. Recarregue antes de salvar.")
    old_items = {int(p["product_id"]): p for p in old["items"]}
    try:
        validate_campaign_draft_items(body.items, list(old_items))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    items = []
    for item in body.items:
        saved = item.model_dump(mode="json")
        saved["source_image"] = old_items[item.product_id].get("source_image")
        saved["use_shopee_image"] = bool(saved["source_image"]) and item.use_shopee_image
        items.append(saved)
    update = {"items": items,
              "schedule": body.schedule.model_dump(mode="json") if body.schedule else None,
              "revision": body.expected_revision + 1,
              "updated_at": datetime.now(timezone.utc).isoformat()}
    result = (scope_owner(supabase.table("campaign_drafts").update(update)
              .eq("id", str(draft_id)).eq("status", "draft")
              .eq("revision", body.expected_revision), user_id, profile_id).execute())
    if not result.data:
        raise HTTPException(status_code=409, detail="Rascunho modificado por outra sessão.")
    return result.data[0]
