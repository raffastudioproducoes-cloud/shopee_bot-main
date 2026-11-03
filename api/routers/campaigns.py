"""Prévia de campanhas por listas — leitura apenas, sem persistência/ativação.

A API só calcula horários para uma lista do usuário e perfil ativo;
a futura execução exige políticas de rede, idempotência e congelamento T-30.
"""
from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..campaign_schedule import plan_campaign_slots
from .auth import get_current_user_id
from .profiles import get_current_profile_id
from .lists import _get_list, _get_list_products


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
