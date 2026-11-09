"""F4E: activation pipeline; no social network POST is performed here.

Every reservation is inert until private assets, live OAuth and atomic
post/scheduler/job materialization have all succeeded. Retrying a request is
idempotent; a failure leaves the reservation in a non-dispatchable state.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import PurePosixPath

from fastapi import HTTPException

from .campaign_schedule import plan_campaign_slots
from .campaign_policy import (
    load_campaign_policy, require_campaign_access,
    validate_campaign_plan_schedule, validate_campaign_network_volume,
)
from .media_composition import plan_network_composition
from .network_limits import is_network_disabled
from .campaign_product_media import synchronize_product_media
from .database import supabase
from .storage_capacity import storage_upload_reservation
from .media_sanitizer import sanitize_media_upload, detect_media_type
from .routers.posts import (
    MEDIA_DRAFT_BUCKET, _download_shopee_image,
    _normalize_shopee_photo_as_jpeg, MAX_PRODUCT_IMAGE_BYTES,
)
from .routers.credentials import _autotest_outcome
from shopee_bot.database.scheduler_environment import current_environment

logger = logging.getLogger(__name__)
ALLOWED_NETWORKS = {"threads", "x", "facebook", "instagram", "tiktok"}
MAX_OCCURRENCES = 450


def _rpc(name: str, args: dict):
    try:
        result = supabase.rpc(name, args).execute()
        return result.data
    except Exception as exc:
        # Never leak provider tokens, private paths or raw PostgREST exceptions.
        logger.warning("RPC de campanha %s recusada (%s)", name, type(exc).__name__)
        reason = str(exc)
        if "campaign_active_days_exceeded" in reason:
            raise HTTPException(403, detail="O limite de dias de publicação do plano foi atingido.") from None
        if "campaign_window_exceeded" in reason:
            raise HTTPException(422, detail="O intervalo ultrapassa o limite de 210 dias corridos.") from None
        if "invalid_campaign_weekdays" in reason:
            raise HTTPException(422, detail="Selecione dias da semana válidos.") from None
        if "campaign_quota_exceeded" in reason:
            raise HTTPException(403, detail="O limite de campanhas ativas do plano foi atingido.") from None
        if "paid_period_not_confirmed" in reason or "campaign_outside_paid_period" in reason:
            raise HTTPException(403, detail="O período pago não cobre todos os horários selecionados.") from None
        if "campaign_day_slots_exceeded" in reason:
            raise HTTPException(403, detail="A quantidade diária de postagens excede o limite do plano.") from None
        raise HTTPException(409, detail="A operação da campanha foi recusada. Confira plano, cotas e horário; atualize o painel.") from None


def owned_reservation(reservation_id, user_id, profile_id):
    row = (supabase.table("campaign_reservations_f4e").select(
        "id,draft_id,request_key,lifecycle,source_environment,activated_at,pause_reason,created_at,draft_snapshot")
        .eq("id", str(reservation_id)).eq("user_id", str(user_id))
        .eq("profile_id", str(profile_id)).maybe_single().execute())
    if not row or not row.data:
        raise HTTPException(404, detail="Campanha não encontrada neste perfil.")
    record = dict(row.data)
    record["name"] = (record.pop("draft_snapshot",{}) or {}).get("campaign_name") or "Campanha"
    return record


def reservation_details(reservation_id, user_id, profile_id):
    row = owned_reservation(reservation_id, user_id, profile_id)
    progress = (supabase.table("campaign_progress_f4e").select("*")
        .eq("reservation_id", str(reservation_id)).eq("user_id", str(user_id))
        .eq("profile_id", str(profile_id)).maybe_single().execute())
    return {**row, "progress": progress.data if progress else None}


def _final_text(item: dict, network: str):
    body = (item.get("network_copies") or {}).get(network) or item.get("copy") or ""
    url = item.get("affiliate_link") or ""
    if url and url not in body:
        return "\n".join(x for x in (body.strip(), url) if x)
    return body.strip()


def _media_sources(reservation: dict):
    media = []
    for row in reservation["media_snapshot"]:
        if row.get("status") != "ready" or row.get("storage_bucket") != MEDIA_DRAFT_BUCKET:
            raise HTTPException(422, detail="Há anexo sem confirmação de armazenamento.")
        key = row.get("storage_key") or ""
        prefix = ("campaigns/" + str(reservation["user_id"]) + "/" +
                  str(reservation["profile_id"]) + "/" + str(reservation["draft_id"]) + "/")
        if not key.startswith(prefix):
            raise HTTPException(422, detail="Referência de anexo fora da campanha.")
        media.append({
            "source_id": "draft:" + str(row["id"]), "product_id": int(row["product_id"]),
            "file_name": row["file_name"], "type": row["media_type"],
            "size": int(row["size_bytes"]), "storage_key": key,
            "from_shopee": False,
        })
    for item in reservation["draft_snapshot"]["items"]:
        if item.get("use_shopee_image") and item.get("source_image"):
            media.append({
                "source_id": "shopee:" + str(item["product_id"]),
                "product_id": int(item["product_id"]),
                "file_name": "shopee-" + str(item["product_id"]) + ".jpg",
                "type": "IMAGE", "size": 0,
                "source_image": item["source_image"], "from_shopee": True,
            })
    return media


async def _prepare_shopee_sources(sources):
    """Download and sanitize selected Shopee photos once so each network's byte limit is real."""
    for source in sources:
        if not source.get("from_shopee"):
            continue
        content = await _download_shopee_image(source["source_image"])
        detected = detect_media_type(content)
        if detected.media_type != "IMAGE":
            raise HTTPException(415, detail="A foto Shopee não é uma imagem.")
        media = await asyncio.to_thread(
            sanitize_media_upload, content,
            filename="shopee-" + str(source["product_id"]) + ".jpg",
            content_type=detected.mime_type, max_bytes=MAX_PRODUCT_IMAGE_BYTES,
        )
        media = await asyncio.to_thread(_normalize_shopee_photo_as_jpeg, media, source["product_id"])
        source["prepared_media"] = media
        source["size"] = len(media.content)
        source["type"] = "IMAGE"
    return sources


def _validate_plans(reservation, sources=None):
    draft = reservation["draft_snapshot"]
    sources = sources if sources is not None else _media_sources(reservation)
    selected_networks = set()
    compat = {source["source_id"]: set() for source in sources}
    for item in draft["items"]:
        pid = int(item["product_id"])
        medias = [s for s in sources if s["product_id"] == pid]
        for network in item["networks"]:
            if network not in ALLOWED_NETWORKS:
                raise HTTPException(422, detail="Uma rede da campanha não é suportada.")
            reason = is_network_disabled(network)
            if reason:
                raise HTTPException(422, detail=reason)
            plan = plan_network_composition(
                network, [_final_text(item, network)],
                [{"id": s["source_id"], "file_name": s["file_name"], "type": s["type"], "size": s["size"]}
                 for s in medias],
                product_count=1,
            )
            if plan.mode == "blocked":
                raise HTTPException(422, detail=plan.blocked_reason or "Mídia incompatível.")
            for source_id in plan.media_ids:
                compat[source_id].add(network)
            selected_networks.add(network)
    if not selected_networks:
        raise HTTPException(422, detail="Selecione ao menos uma rede para a campanha.")
    return sources, compat, selected_networks


async def _copy_locked_asset(reservation, source, networks):
    user = str(reservation["user_id"])
    profile = str(reservation["profile_id"])
    res_id = str(reservation["id"])
    key = (f"campaign-locked/{user}/{profile}/{res_id}/"
           f"{source['product_id']}/{uuid.uuid4().hex}"
           f"{PurePosixPath(source['file_name']).suffix.lower() if not source['from_shopee'] else '.jpg'}")
    copied = False
    size = source["size"]
    try:
        if source["from_shopee"]:
            media = source.get("prepared_media")
            if media is None:
                content = await _download_shopee_image(source["source_image"])
                detected = detect_media_type(content)
                if detected.media_type != "IMAGE":
                    raise HTTPException(415, detail="A foto Shopee não é uma imagem.")
                media = await asyncio.to_thread(
                    sanitize_media_upload, content,
                    filename="shopee-" + str(source["product_id"]) + detected.extension,
                    content_type=detected.mime_type, max_bytes=MAX_PRODUCT_IMAGE_BYTES,
                )
                media = await asyncio.to_thread(_normalize_shopee_photo_as_jpeg, media, source["product_id"])
            size = len(media.content)
            with storage_upload_reservation(size):
                supabase.storage.from_(MEDIA_DRAFT_BUCKET).upload(
                    key, media.content, {"content-type": media.mime_type, "upsert": "false"})
            copied = True
        else:
            with storage_upload_reservation(size):
                supabase.storage.from_(MEDIA_DRAFT_BUCKET).copy(source["storage_key"], key)
            copied = True
        _rpc("record_campaign_asset_f4e", {
            "p_user": user, "p_profile": profile, "p_reservation": res_id,
            "p_product": source["product_id"], "p_source": source["source_id"],
            "p_key": key, "p_name": source["file_name"], "p_type": source["type"],
            "p_size": size, "p_networks": sorted(networks),
        })
    except HTTPException:
        if copied:
            try: supabase.storage.from_(MEDIA_DRAFT_BUCKET).remove([key])
            except Exception: logger.warning("Cópia incompleta mantida para limpeza posterior")
        raise
    except Exception as exc:
        logger.warning("Falha de retenção da campanha (%s)", type(exc).__name__)
        if copied:
            try: supabase.storage.from_(MEDIA_DRAFT_BUCKET).remove([key])
            except Exception: logger.warning("Cópia incompleta mantida para limpeza posterior")
        raise HTTPException(502, detail="Não foi possível reter uma mídia da campanha. Tente novamente.") from None


async def activate(draft_id, expected_revision, user_id, profile_id):
    from .routers.campaigns import (
        _get_owned_campaign, CampaignPreviewRequest, CampaignDraftItem,
        validate_campaign_draft_schedule,
    )
    policy = load_campaign_policy(user_id, profile_id)
    require_campaign_access(policy)
    draft = _get_owned_campaign(draft_id, user_id, profile_id)
    if draft["status"] != "draft" or int(draft["revision"]) != expected_revision:
        raise HTTPException(409, detail="Rascunho alterado. Recarregue antes de ativar.")
    if not draft.get("schedule"):
        raise HTTPException(422, detail="Configure o período da campanha.")
    schedule = CampaignPreviewRequest.model_validate(draft["schedule"])
    items = [CampaignDraftItem.model_validate(item) for item in draft["items"]]
    # Snapshot congelado deve estar associado ao ID atual da conta. Não
    # reescrever jobs já agendados, nem autorizar publicação com link antigo.
    from .routers.platform_shopee import get_affiliate_id
    from .shopee_affiliate_links import canonical_product_url, build_affiliate_link
    affiliate_id = (get_affiliate_id(user_id) if any(
        canonical_product_url(i.get("source_original_link")) for i in draft["items"]) else None)
    for item in draft["items"]:
        original = item.get("source_original_link")
        if canonical_product_url(original):
            expected = build_affiliate_link(original, affiliate_id)
            if not expected or item.get("affiliate_link") != expected:
                raise HTTPException(409, detail="O ID de afiliado mudou. Reabra e salve o rascunho antes de ativar.")
    validate_campaign_plan_schedule(policy, schedule)
    validate_campaign_network_volume(policy, schedule, items)
    validate_campaign_draft_schedule(schedule, draft["source_list_id"], [i.product_id for i in items])
    slots = plan_campaign_slots(
        start_date=schedule.start_date,end_date=schedule.end_date,
        weekdays=schedule.weekdays,start_time=schedule.start_time,
        end_time=schedule.end_time,posts_per_day=schedule.posts_per_day,
        item_ids=schedule.item_ids,timezone="America/Sao_Paulo",
    )
    if not slots or len(slots) > MAX_OCCURRENCES:
        raise HTTPException(422, detail="A campanha deve ter de 1 a 450 horários.")
    cutoff = datetime.now(timezone.utc) + timedelta(minutes=30)
    if any(slot.utc_at <= cutoff for slot in slots):
        raise HTTPException(422, detail="Todos os horários devem estar ao menos 30 minutos no futuro.")

    # Populate the existing private campaign-draft media pipeline from selected
    # product assets, without uploading again from the browser. The RPC below
    # then snapshots these same profile-scoped rows atomically as before.
    request_key = f"activate:{draft_id}:{expected_revision}"
    existing_reservation = (supabase.table("campaign_reservations_f4e").select("id")
        .eq("draft_id", str(draft_id)).eq("user_id", str(user_id))
        .eq("profile_id", str(profile_id)).eq("request_key", request_key)
        .limit(1).execute()).data or []
    if not existing_reservation:
        await asyncio.to_thread(
            synchronize_product_media, str(draft_id), str(user_id), str(profile_id), draft["items"],
        )

    # This identifier survives a network timeout or browser retry.
    reservation_id = _rpc("reserve_campaign_networks_f4e", {
        "p_user_id": str(user_id), "p_profile_id": str(profile_id),
        "p_draft_id": str(draft_id), "p_revision": expected_revision,
        "p_request_key": request_key,
        "p_occurrences": [slot.utc_at.strftime("%Y-%m-%dT%H:%M:%SZ") for slot in slots],
    })
    row = (supabase.table("campaign_reservations_f4e").select("*")
        .eq("id", str(reservation_id)).eq("user_id", str(user_id))
        .eq("profile_id", str(profile_id)).single().execute()).data
    if row["lifecycle"] == "active":
        return reservation_details(reservation_id,user_id,profile_id)
    if row["lifecycle"] != "preparing":
        raise HTTPException(409, detail="Campanha não está mais em preparação.")

    sources = _media_sources(row)
    await _prepare_shopee_sources(sources)
    sources, compat, networks = _validate_plans(row, sources)
    existing = (supabase.table("campaign_reservation_assets_f4e")
        .select("source_id").eq("reservation_id", str(reservation_id)).execute()).data or []
    done = {r["source_id"] for r in existing}
    for source in sources:
        if source["source_id"] not in done:
            await _copy_locked_asset(row,source,compat[source["source_id"]])
    # Validate permissions live, after storage work; no remote publication here.
    for network in sorted(networks):
        try:
            state, _ = await asyncio.to_thread(_autotest_outcome,network,user_id,profile_id)
        except Exception as exc:
            logger.warning("OAuth %s indisponível: %s",network,type(exc).__name__)
            raise HTTPException(409, detail=f"Não foi possível validar a permissão OAuth de {network}.") from None
        if state != "ok":
            raise HTTPException(409, detail=f"Conexão ou permissão OAuth de {network} não está pronta.")
        supabase.table("campaign_oauth_checks_f4e").upsert({
            "reservation_id": str(reservation_id), "network": network,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        },on_conflict="reservation_id,network").execute()
    _rpc("materialize_campaign_f4e", {
        "p_user": str(user_id),"p_profile": str(profile_id),
        "p_reservation": str(reservation_id),"p_environment": current_environment(),
    })
    return reservation_details(reservation_id,user_id,profile_id)
