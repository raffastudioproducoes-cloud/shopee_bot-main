"""Link saved product assets to campaign draft media only upon activation.

The browser only submits IDs. This backend validates account ownership and
copies private Storage objects into the existing profile-isolated campaign
pipeline, preserving the atomic reservation and locked-asset semantics.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from fastapi import HTTPException

from .database import supabase
from .profiles import scope_account, scope_owner
from .storage_capacity import storage_upload_reservation

logger = logging.getLogger(__name__)
BUCKET = "post-media"
MAX_PER_PRODUCT = 10


def _linked_id(draft_id: str, asset_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"auto-orbital:campaign:{draft_id}:product-media:{asset_id}"))


def synchronize_product_media(draft_id: str, user_id: str, profile_id: str, items: list[dict]) -> None:
    """Idempotently prepare only selected product media, preserving legacy uploads.

    This runs before the existing reservation RPC takes its atomic media snapshot.
    Nothing is published and the product gallery is never modified.
    """
    selections = {str(media_id): int(item["product_id"]) for item in items
                  for media_id in item.get("product_media_ids", [])}
    if len(selections) != sum(len(item.get("product_media_ids", [])) for item in items):
        raise HTTPException(422, detail="Uma mídia não pode ser selecionada para produtos diferentes.")

    sources = {}
    if selections:
        records = (scope_account(supabase.table("product_media").select("*")
                   .in_("id", list(selections)), user_id).execute()).data or []
        sources = {str(row["id"]): row for row in records}
        if any(asset not in sources or sources[asset]["status"] != "ready" or
               int(sources[asset]["product_id"]) != pid for asset, pid in selections.items()):
            raise HTTPException(409, detail="Uma mídia do produto foi removida ou está indisponível. Revise a seleção.")

    rows = (scope_owner(supabase.table("campaign_draft_media").select("*")
            .eq("campaign_id", draft_id), user_id, profile_id).execute()).data or []
    prefix = f"campaigns/{user_id}/{profile_id}/{draft_id}/"
    wanted = {_linked_id(draft_id, asset_id): asset_id for asset_id in selections}

    legacy_counts: dict[int, int] = defaultdict(int)
    selected_counts: dict[int, int] = defaultdict(int)
    for row in rows:
        linked_prefix = prefix + str(row["product_id"]) + "/linked/"
        if not str(row["storage_key"]).startswith(linked_prefix):
            legacy_counts[int(row["product_id"])] += 1
    for product_id in selections.values():
        selected_counts[product_id] += 1
    if any(legacy_counts[pid] + count > MAX_PER_PRODUCT for pid, count in selected_counts.items()):
        raise HTTPException(422, detail="Esta seleção excede 10 mídias, incluindo anexos antigos da campanha.")

    # A derived link is distinguished by its exact path segment, not the
    # user-controlled filename. Legacy independent campaign uploads are untouched.
    for row in rows:
        linked_prefix = prefix + str(row["product_id"]) + "/linked/"
        if not str(row["storage_key"]).startswith(linked_prefix):
            continue
        if row["id"] in wanted:
            if row["status"] != "ready":
                raise HTTPException(409, detail="Uma mídia da campanha não terminou de ser preparada.")
            continue
        try:
            supabase.storage.from_(BUCKET).remove([row["storage_key"]])
            scope_owner(supabase.table("campaign_draft_media").delete()
                        .eq("campaign_id", draft_id).eq("id", row["id"]), user_id, profile_id).execute()
        except Exception:
            logger.warning("Falha ao remover referência desmarcada da campanha", exc_info=True)
            raise HTTPException(502, detail="Não foi possível atualizar a seleção de mídias da campanha.") from None

    kept = [row for row in rows if row["id"] in wanted or not str(row["storage_key"]).startswith(
        prefix + str(row["product_id"]) + "/linked/")]
    occupied: dict[int, set[int]] = defaultdict(set)
    for row in kept:
        occupied[int(row["product_id"])].add(int(row["slot"]))

    for asset_id, product_id in selections.items():
        new_id = _linked_id(draft_id, asset_id)
        if any(str(row["id"]) == new_id for row in kept):
            continue
        source = sources[asset_id]
        origin_key = source["storage_key"]
        origin_prefix = f"products/{user_id}/{product_id}/"
        if not origin_key.startswith(origin_prefix) or not origin_key.endswith((".mp4", ".jpg", ".png", ".gif", ".webp")):
            raise HTTPException(409, detail="Referência de mídia do produto inválida.")
        slot = next((n for n in range(MAX_PER_PRODUCT) if n not in occupied[product_id]), None)
        if slot is None:
            raise HTTPException(422, detail="Limite de 10 mídias por produto nesta campanha.")
        extension = origin_key.rsplit(".", 1)[-1]
        target_key = f"{prefix}{product_id}/linked/{new_id}.{extension}"
        record = {
            "id": new_id, "campaign_id": draft_id, "user_id": user_id, "profile_id": profile_id,
            "product_id": product_id, "slot": slot,
            "storage_bucket": BUCKET, "storage_key": target_key,
            "file_name": source["file_name"], "mime_type": source["mime_type"],
            "media_type": source["media_type"], "size_bytes": source["size_bytes"],
            "status": "uploading",
        }
        try:
            inserted = supabase.table("campaign_draft_media").insert(record).execute()
            if not inserted.data:
                raise RuntimeError("campaign media row missing")
            with storage_upload_reservation(int(source["size_bytes"])):
                supabase.storage.from_(BUCKET).copy(origin_key, target_key)
            ready = scope_owner(supabase.table("campaign_draft_media").update({"status": "ready"})
                                .eq("id", new_id).eq("campaign_id", draft_id), user_id, profile_id).execute()
            if not ready.data:
                raise RuntimeError("campaign media not ready")
        except Exception:
            logger.warning("Falha ao preparar cópia privada da mídia selecionada", exc_info=True)
            try:
                supabase.storage.from_(BUCKET).remove([target_key])
                scope_owner(supabase.table("campaign_draft_media").delete()
                            .eq("id", new_id).eq("campaign_id", draft_id), user_id, profile_id).execute()
            except Exception:
                logger.warning("Falha de compensação da cópia de campanha", exc_info=True)
            raise HTTPException(502, detail="Falha ao preparar mídia do produto para a campanha. Tente novamente.") from None
        occupied[product_id].add(slot)
