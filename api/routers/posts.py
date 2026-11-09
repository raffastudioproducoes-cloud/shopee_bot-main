"""
Posts Router — API Python (FastAPI)

CRUD de posts (thread multi-parte) + copywriter IA + agendamento/
publicação. Agendamento/publicação passam pelo bridge interno
(`api/internal_client.py` -> `web/routes/internal.py`) porque o
APScheduler só roda de verdade no processo Flask — ver docstring de
internal_client.py e Fase 8 em docs/ROADMAP_MIGRACAO.md.

Upload de mídia (imagem/vídeo) valida e sanitiza o conteúdo e o armazena
no bucket privado `post-media` do Supabase Storage, com referência durável
`storage://` por usuário e perfil. Os publicadores obtêm URLs assinadas
temporárias; não há dependência do filesystem do Render nem de CDN externo.
Simplificação: mídia só na head da thread, não em cada parte.

Modelo de thread: cada parte é uma linha em `posts`; a primeira
("head", a única retornada por list_posts) tem `post_id IS NULL`; cada
parte seguinte tem `post_id` apontando pra parte ANTERIOR (lista
encadeada por trás pra frente, não por índice). Produtos, agendamento
e `network` sempre grudam na head. `network` escolhe a função chamada
pelo scheduler via `NETWORK_FUNC_MAP` (definido neste módulo).
Os cinco publicadores do mapa são acionados pelo scheduler. Threads, Facebook
e Instagram têm caminho de imagem; X ainda precisa de upload de mídia e acesso
à API, e TikTok Photo Direct Post exige URL pública verificada e Creator Info no
fluxo do usuário. Kwai fica de fora do mapa, sem API pública confirmada.
"""

import logging
import time
import uuid
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlparse
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, model_validator, field_validator

from .auth import _check_login_rate_limit, get_current_user_id
from .profiles import get_current_profile_id
from ..profiles import scope_account, scope_owner
from ..plan_quotas import reserve_post_plan_quota, release_failed_post_plan_quota
from ..audit_log import log_action
from ..database import supabase
from shopee_bot.database.scheduler_environment import current_environment
from ..storage_capacity import storage_upload_reservation
from ..utils.log_sanitizer import sanitize_log_data
from ..network_limits import validate_post, errors_detail, is_network_disabled
from ..media_composition import plan_network_composition
from ..media_sanitizer import MediaSanitizerError, sanitize_media_upload, detect_media_type
from ..media_upload_pipeline import prepare_media_upload
from ..shopee_images import (
    SHOPEE_IMAGE_HOSTS, MAX_PRODUCT_IMAGE_BYTES,
    _check_shopee_image_url, _download_shopee_image,
)
from .. import x_oauth
from ..text_variants import generate_variants, generate_thread_replies, generate_short_product_description, MAX_THREAD_PARTS
from ..internal_client import (
    create_scheduler_job,
    scheduler_availability,
    remove_scheduler_job,
    run_scheduler_job,
    InternalApiError,
)

logger = logging.getLogger(__name__)

# Rede social do post -> função de publicação chamada pelo scheduler
# (mesmo mapa usado no painel Flask legado, ver database/schedulers.py
# — duplicado aqui porque api/database.py é o client Supabase, um
# módulo totalmente separado do database/ psycopg usado pelo Flask;
# não vale a pena acoplar os dois runtimes por causa de um dict de 5
# linhas). Kwai fica de fora: sem API pública confirmada ainda.
NETWORK_FUNC_MAP = {
    "threads": "bot_post",
    "x": "bot_post_x",
    "facebook": "bot_post_facebook",
    "instagram": "bot_post_instagram",
    "tiktok": "bot_post_tiktok",
}
NetworkLiteral = Literal[tuple(NETWORK_FUNC_MAP.keys())]

MEDIA_ROOT = Path("web/media")
MAX_MEDIA_BYTES = 50 * 1024 * 1024  # 50MB, mesmo teto do Flask (FLASK_MAX_CONTENT_LENGTH)
MEDIA_DRAFT_BUCKET = "post-media"
MEDIA_DRAFT_TTL = timedelta(hours=24)

STORAGE_SCHEME = "storage://"


def _parse_storage_path(file_path: str) -> tuple[str, str] | None:
    """`storage://bucket/chave` -> (bucket, chave); None se não for confiável.

    `file_path` vem do banco: só aceita o bucket de mídia esperado e chave sem
    segmentos vazios ou `..`, pra nunca apagar fora do que a API gravou."""
    bucket, _, key = file_path[len(STORAGE_SCHEME):].partition("/")
    segments = key.split("/")
    if bucket != MEDIA_DRAFT_BUCKET or not key or any(s in ("", ".", "..") for s in segments):
        return None
    return bucket, key


def _remove_durable_media(file_path: str) -> None:
    parsed = _parse_storage_path(file_path)
    if parsed is None:
        logger.warning("Remoção de mídia durável fora do bucket esperado recusada: %s", file_path)
        return
    bucket, key = parsed
    try:
        supabase.storage.from_(bucket).remove([key])
        # a linha `consumed` do rascunho morre junto com o objeto
        supabase.table("temporary_media_uploads").delete()             .eq("storage_bucket", bucket).eq("storage_key", key).eq("status", "consumed").execute()
    except Exception:
        logger.warning("Falha ao remover mídia durável %s", file_path, exc_info=True)


def _remove_media_file(file_path: str) -> None:
    """Apaga o arquivo de uma mídia. `storage://` -> objeto do Storage; senão
    só se estiver dentro de MEDIA_ROOT — `file_path` vem do banco e pode ter
    sido gravado por versões antigas sem sanitização (ex.:
    "web/media/1/../../../x")."""
    if file_path.startswith(STORAGE_SCHEME):
        _remove_durable_media(file_path)
        return
    resolved = Path(file_path).resolve()
    if not resolved.is_relative_to(MEDIA_ROOT.resolve()):
        logger.warning("Remoção de mídia fora de MEDIA_ROOT recusada: %s", file_path)
        return
    try:
        resolved.unlink(missing_ok=True)  # já sumiu: não bloqueia a remoção do post
    except OSError:
        logger.warning("Falha ao remover arquivo de mídia %s", file_path, exc_info=True)


def _remove_draft_from_storage(draft: dict) -> None:
    bucket, key = draft.get("storage_bucket"), draft.get("storage_key")
    if bucket and key:
        supabase.storage.from_(bucket).remove([key])


def _draft_response(draft: dict) -> dict:
    """Não entrega chave de Storage, URL assinada nem MIME interno ao cliente."""
    return {
        key: draft.get(key)
        for key in ("id", "file_name", "size_bytes", "media_type", "profile_id", "status", "expires_at", "created_at")
    }


def _expired_at(value: object, now: datetime) -> bool:
    if not value:
        return False
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return False
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment <= now


async def _read_media_content(file: UploadFile) -> bytearray:
    """Lê em blocos e recusa um upload antes de acumular mais de 50 MB.

    Devolve o bytearray sem copiar pra bytes (evita 2x 50 MB); o sanitizador
    aceita ambos e sempre devolve bytes."""
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > MAX_MEDIA_BYTES:
            raise HTTPException(status_code=413, detail="Arquivo excede o tamanho máximo (50MB)")
    return content


async def _sanitize_upload(file: UploadFile, content: bytes | bytearray):
    """Valida e reconstrói mídia antes do Storage; falha sem eco do conteúdo."""
    try:
        media = await run_in_threadpool(
            prepare_media_upload,
            content,
            filename=file.filename,
            content_type=file.content_type,
            max_bytes=MAX_MEDIA_BYTES,
        )
        return media
    except MediaSanitizerError as exc:
        logger.info(
            "Upload de midia rejeitado: %s",
            exc,
            extra=sanitize_log_data({
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(content),
            }),
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"Arquivo inválido ou não suportado: {exc}",
        ) from None


def cleanup_expired_media_drafts(now: datetime | None = None) -> int:
    """Limpa somente rascunhos vencidos e prontos, sem tocar em posts.

    A tabela temporária é separada de `medias`, portanto não aciona o trigger
    histórico de `posts_medias` e não pode remover mídia confirmada.
    """
    now = now or datetime.now(timezone.utc)
    result = (
        supabase.table("temporary_media_uploads")
        .select("id, storage_bucket, storage_key, expires_at")
        .in_("status", ["uploading", "ready", "delete_failed"])
        .lte("expires_at", now.isoformat())
        .order("expires_at")
        .limit(100)
        .execute()
    )
    removed = 0
    for draft in result.data or []:
        if not _expired_at(draft.get("expires_at"), now):
            continue
        try:
            _remove_draft_from_storage(draft)
        except Exception:
            logger.warning("Falha ao limpar rascunho de mídia expirado", exc_info=True)
            supabase.table("temporary_media_uploads").update({"status": "delete_failed"}).eq("id", draft["id"]).execute()
            continue
        supabase.table("temporary_media_uploads").delete().eq("id", draft["id"]).execute()
        removed += 1
    return removed


router = APIRouter(prefix="/posts", tags=["posts"])


# ── Schemas ──────────────────────────────────────────────────────────────────────

class PostSchedule(BaseModel):
    trigger: Literal["cron", "date"]
    time: str | None = None  # "HH:MM", obrigatório se trigger=cron
    times: list[str] | None = None  # até cinco horários por dia escolhido
    # Campo legado: permanece para jobs antigos e para o primeiro dia da lista.
    day_of_week: int | None = None
    # Novo contrato: um a sete dias, 0=segunda-feira ... 6=domingo.
    days_of_week: list[int] | None = None
    start_date: str | None = None  # ISO 8601, opcional em cron
    run_date: str | None = None  # ISO 8601, obrigatório se trigger=date

    @model_validator(mode="after")
    def _check_required_fields(self):
        if self.trigger == "cron":
            days = self.days_of_week if self.days_of_week is not None else ([self.day_of_week] if self.day_of_week is not None else None)
            times = self.times if self.times is not None else ([self.time] if self.time is not None else None)
            if not times or not days:
                raise ValueError("time e ao menos um dia da semana são obrigatórios para trigger 'cron'")
            if len(times) > 5 or len(set(times)) != len(times) or any(not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) for value in times):
                raise ValueError("times deve conter de um a cinco horários HH:MM únicos")
            if self.time is not None and self.times is not None and self.time != times[0]:
                raise ValueError("time deve corresponder ao primeiro item de times")
            if len(days) > 7 or len(set(days)) != len(days) or any(not isinstance(day, int) or day < 0 or day > 6 for day in days):
                raise ValueError("days_of_week deve ter de um a sete dias únicos entre 0 e 6")
            if self.day_of_week is not None and self.days_of_week is not None and self.day_of_week != days[0]:
                raise ValueError("day_of_week deve corresponder ao primeiro item de days_of_week")
            self.days_of_week = days
            self.day_of_week = days[0]
            self.times = times
            self.time = times[0]
        if self.trigger == "date" and self.run_date is None:
            raise ValueError("run_date é obrigatório para trigger 'date'")
        return self


class PostCreate(BaseModel):
    texts: list[str]  # 1 item = post único; 2+ = thread encadeada
    product_ids: list[int] = []
    schedule: PostSchedule
    network: NetworkLiteral = "threads"
    # Publicação multi-rede: os posts das outras redes reaproveitam a mídia
    # já enviada pro primeiro (mesma linha em `medias`, sem reenviar).
    media_ids: list[int] = []
    # Mesmo UUID em todos os posts de um envio multi-rede (selo "Grupo").
    group_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _only_recurring_for_legacy_create(self):
        if self.schedule.trigger != "cron":
            raise ValueError("Agendamento avulso indisponível. Use Recorrente ou Agora.")
        return self

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, v):
        if not v or not any(t.strip() for t in v):
            raise ValueError("texts precisa ter ao menos um item com texto")
        if len(v) > MAX_THREAD_PARTS:
            raise ValueError(f"Máximo de {MAX_THREAD_PARTS} partes por publicação")
        return v


class PostComposition(BaseModel):
    network: NetworkLiteral
    texts: list[str]

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, value):
        if not value or not any(text.strip() for text in value):
            raise ValueError("texts precisa ter ao menos um item com texto")
        if len(value) > MAX_THREAD_PARTS:
            raise ValueError(f"Máximo de {MAX_THREAD_PARTS} partes por publicação")
        return value


class PostBatchCreate(BaseModel):
    compositions: list[PostComposition]
    product_ids: list[int] = []
    draft_media_ids: list[str] = []
    schedule: PostSchedule
    publish_immediately: bool = False

    @field_validator("draft_media_ids")
    @classmethod
    def _draft_ids_are_unique_uuids(cls, value):
        """UUID inválido vira 422 (não 500 no banco); duplicata sai, mantendo a
        ordem, pra não quebrar a PK (post_id, media_id) de posts_medias."""
        try:
            normalized = [str(uuid.UUID(item)) for item in value]
        except (ValueError, AttributeError, TypeError):
            raise ValueError("draft_media_ids deve conter apenas UUIDs") from None
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def _check_networks(self):
        if self.publish_immediately and self.schedule.trigger != "date":
            raise ValueError("Publicar agora requer a reserva interna de data")
        if not self.publish_immediately and self.schedule.trigger != "cron":
            raise ValueError("Agendamento avulso indisponível. Escolha Recorrente ou Agora.")
        networks = [composition.network for composition in self.compositions]
        if not networks:
            raise ValueError("Escolha ao menos uma rede")
        if len(networks) != len(set(networks)):
            raise ValueError("Cada rede pode aparecer apenas uma vez")
        return self


class PostUpdate(BaseModel):
    texts: list[str]
    product_ids: list[int] = []

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, v):
        if not v or not any(t.strip() for t in v):
            raise ValueError("texts precisa ter ao menos um item com texto")
        if len(v) > MAX_THREAD_PARTS:
            raise ValueError(f"Máximo de {MAX_THREAD_PARTS} partes por publicação")
        return v


class GenerateCopyBody(BaseModel):
    product_id: int
    persona: str = "casual"
    # Compatibilidade com clientes antigos. O backend usa SOMENTE o provedor
    # ativo da plataforma, ignorando qualquer valor enviado pelo usuário.
    provider: str | None = None
    # Redes marcadas: uma versão individual por rede (api/text_variants.py).
    networks: list[NetworkLiteral] = []
    # 1 = comportamento legado; 2..10 gera todas as partes em sequência.
    part_count: int = Field(default=1, ge=1, le=MAX_THREAD_PARTS)
    mode: Literal["full", "append"] = "full"
    existing_texts: list[str] = []
    # Na personalização, usa o mesmo gerador mas sem link e com teto X=280.
    description_only: bool = False

    @model_validator(mode="after")
    def _valid_generation_mode(self):
        if self.description_only and (self.mode != "full" or self.part_count != 1 or self.existing_texts or self.networks):
            raise ValueError("Descrição de produto exige apenas uma parte, sem redes ou continuação.")
        if self.mode == "append":
            if (not self.existing_texts or
                    len(self.existing_texts) >= self.part_count or
                    any(not text.strip() for text in self.existing_texts)):
                raise ValueError("append exige partes anteriores preenchidas e novas partes disponíveis")
        elif self.existing_texts:
            raise ValueError("existing_texts só é válido no modo append")
        return self


# ── Helpers ──────────────────────────────────────────────────────────────────────

def _get_post(user_id: int, post_id: int, profile_id: str | None = None) -> dict:
    """Busca o post verificando dono e, com perfil ativo, o perfil (evita
    IDOR entre perfis da mesma conta)."""
    result = (
        scope_owner(supabase.table("posts").select("*").eq("id", post_id), user_id, profile_id)
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


def _get_post_medias(post_id: int) -> list[dict]:
    result = (
        supabase.table("posts_medias")
        .select("display_order, medias(id, file_name, size, type)")
        .eq("post_id", post_id)
        .order("display_order")
        .execute()
    )
    medias: list[dict] = []
    for item in result.data or []:
        media = item.get("medias")
        if media:
            medias.append(media)
    return medias


def _validate_product_ids(user_id: int, product_ids: list[int]) -> None:
    """400 se algum produto não pertence à conta do usuário;
    evita associar produto alheio ao post (IDOR). Chamar ANTES de qualquer escrita."""
    wanted = set(product_ids)
    if len(product_ids) > 1:
        raise HTTPException(status_code=422, detail="Selecione no máximo um produto por post")
    if not wanted:
        return
    owned = (
        scope_account(supabase.table("products").select("id"), user_id)
        .in_("id", list(wanted))
        .execute()
    )
    if wanted - {row["id"] for row in (owned.data or [])}:
        raise HTTPException(status_code=400, detail="Produto inválido")


def _set_post_products(post_id: int, product_ids: list[int]) -> None:
    supabase.table("posts_products").delete().eq("post_id", post_id).execute()
    if product_ids:
        supabase.table("posts_products").insert([
            {"post_id": post_id, "product_id": pid, "display_order": i}
            for i, pid in enumerate(product_ids)
        ]).execute()


def _require_profile_id(profile_id: str | None) -> str:
    if not profile_id:
        raise HTTPException(status_code=400, detail="Perfil ativo obrigatório")
    return profile_id


def _check_network_rules(
    network: str, texts: list[str], medias: list[dict], product_count: int,
    check_required_media: bool = False,
) -> None:
    """422 com o motivo por rede se o post não passa nas regras da rede
    (api/network_limits.py, espelho do front)."""
    detail = errors_detail(
        validate_post(network, texts, medias, product_count, check_required_media)
    )
    if detail:
        raise HTTPException(status_code=422, detail=detail)


def _check_network_enabled(network: str) -> None:
    reason = is_network_disabled(network)
    if reason:
        raise HTTPException(status_code=422, detail=reason)


def _get_owned_medias(user_id: int, media_ids: list[int], profile_id: str | None) -> list[dict]:
    """Mídias reaproveitadas na criação multi-rede: 400 se alguma não é do
    usuário/perfil (IDOR)."""
    if not media_ids:
        return []
    owned = (
        scope_owner(supabase.table("medias").select("id, file_name, size, type"), user_id, profile_id)
        .in_("id", list(set(media_ids)))
        .execute()
    )
    by_id = {row["id"]: row for row in (owned.data or [])}
    if set(media_ids) - set(by_id):
        raise HTTPException(status_code=400, detail="Mídia inválida")
    return [by_id[mid] for mid in media_ids]


def _get_owned_ready_drafts(user_id: int, draft_ids: list[str], profile_id: str) -> list[dict]:
    """Rascunhos só podem ser consumidos uma vez, pelo mesmo perfil."""
    if not draft_ids:
        return []
    result = (
        scope_owner(
            supabase.table("temporary_media_uploads").select("*").in_("id", list(set(draft_ids))),
            user_id,
            profile_id,
        )
        .eq("status", "ready")
        .execute()
    )
    by_id = {str(row["id"]): row for row in (result.data or [])}
    if set(draft_ids) - set(by_id):
        raise HTTPException(status_code=400, detail="Rascunho de mídia inválido")
    now = datetime.now(timezone.utc)
    if any(_expired_at(by_id[draft_id].get("expires_at"), now) for draft_id in draft_ids):
        raise HTTPException(status_code=400, detail="Um rascunho de mídia expirou. Envie-o novamente.")
    return [by_id[draft_id] for draft_id in draft_ids]


def _create_media_from_draft(draft: dict, user_id: int, profile_id: str) -> dict:
    """Materializa a referência durável sem expor ou copiar o objeto privado."""
    result = (
        supabase.table("medias")
        .insert({
            "user_id": user_id,
            "profile_id": profile_id,
            "file_name": draft["file_name"],
            "file_path": f"storage://{draft['storage_bucket']}/{draft['storage_key']}",
            "size": draft["size_bytes"],
            "type": draft["media_type"],
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Não foi possível preparar a mídia para publicação.")
    return result.data[0]


def _attach_medias(
    head_id: int, draft_ids: list[str], drafts_by_id: dict, materialized: dict,
    fresh: dict, user_id: int, profile_id: str,
) -> list[dict]:
    """Consome (uma vez por rascunho), materializa e vincula as mídias ao post.

    `fresh` mapeia rascunho -> mídia criada por este plano (None entre o claim
    e a criação) pro rollback saber o que desfazer."""
    medias = []
    for order, draft_id in enumerate(draft_ids):
        media = materialized.get(draft_id)
        if not media:
            if not _claim_draft(draft_id, user_id, profile_id):
                raise _DraftUnavailable(draft_id)
            fresh[draft_id] = None
            # Migração 014: um DELETE em posts_medias apaga `medias` sem vínculo,
            # então uma `medias` recém-criada e ainda órfã pode sumir sob um
            # DELETE concorrente. Por isso o vínculo (insert abaixo) vem logo
            # após a criação, sem nenhuma chamada ao banco no meio.
            media = _create_media_from_draft(drafts_by_id[draft_id], user_id, profile_id)
            materialized[draft_id] = media
            fresh[draft_id] = media
        supabase.table("posts_medias").insert({
            "post_id": head_id, "media_id": media["id"], "display_order": order,
        }).execute()
        medias.append(media)
    return medias


SCHEDULER_UNAVAILABLE_MESSAGE = (
    "O agendador de publicações está indisponível neste ambiente. "
    "Seu rascunho foi preservado; nenhuma publicação foi criada."
)


async def _scheduler_is_available() -> bool:
    try:
        return await scheduler_availability()
    except InternalApiError as exc:
        # Nunca expor segredo interno, URL de bridge ou detalhes de rede.
        logger.warning("Consulta de disponibilidade do agendador falhou: %s", type(exc).__name__)
        return False


async def _ensure_scheduler_available() -> None:
    if not await _scheduler_is_available():
        raise HTTPException(status_code=503, detail=SCHEDULER_UNAVAILABLE_MESSAGE)


def _block_reason(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    if isinstance(exc, InternalApiError):
        return "Não foi possível agendar esta rede agora."
    if isinstance(exc, _DraftUnavailable):
        return "Um rascunho de mídia já foi usado. Envie-o novamente."
    return "Não foi possível preparar a mídia desta rede. Tente novamente."


class _DraftUnavailable(Exception):
    """Rascunho já consumido por outra requisição (claim afetou 0 linhas)."""


def _claim_draft(draft_id: str, user_id: int, profile_id: str) -> bool:
    """ready -> consumed condicional e atômico: só uma requisição vence."""
    result = (
        supabase.table("temporary_media_uploads")
        .update({"status": "consumed", "consumed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", draft_id).eq("user_id", user_id).eq("profile_id", profile_id)
        .eq("status", "ready")
        .execute()
    )
    return bool(result.data)


def _release_draft(draft_id: str, user_id: int, profile_id: str) -> None:
    supabase.table("temporary_media_uploads").update(
        {"status": "ready", "consumed_at": None}
    ).eq("id", draft_id).eq("user_id", user_id).eq("profile_id", profile_id).eq("status", "consumed").execute()


def _rollback_plan(
    head_id: int, fresh: dict, materialized: dict, user_id: int, profile_id: str,
) -> None:
    """Desfaz uma rede que falhou: post, vínculos, as mídias criadas só por
    ela e o claim dos rascunhos (voltam a `ready`). Nunca apaga objeto do
    Storage (o rascunho continua utilizável pelas próximas redes)."""
    try:
        for draft_id, media in fresh.items():
            materialized.pop(draft_id, None)
            if media:
                supabase.table("posts_medias").delete().eq("media_id", media["id"]).execute()
                supabase.table("medias").delete().eq("id", media["id"]).execute()
            _release_draft(draft_id, user_id, profile_id)
        _delete_thread_cascade(head_id, user_id)
    except Exception:
        logger.error("Falha ao desfazer post %s após erro no lote", head_id, exc_info=True)


def _media_shared_elsewhere(media_id: int, post_id: int) -> bool:
    """A mesma mídia pode estar ligada a vários posts (grupo multi-rede):
    arquivo e linha em `medias` só somem quando ninguém mais usa."""
    rows = (
        supabase.table("posts_medias").select("post_id").eq("media_id", media_id).execute()
    )
    return any(r.get("post_id") != post_id for r in (rows.data or []))


def _get_post_schedule_entries(user_id: int, post_id: int) -> list[dict]:
    """Retorna todas as ocorrências da agenda, inclusive horários recorrentes."""
    fields = ("id", "trigger", "run_date", "time", "day_of_week", "days_of_week", "start_date")
    result = (
        supabase.table("schedulers").select(",".join(fields))
        .eq("user_id", user_id).eq("post_id", post_id).execute()
    )
    entries = [{field: row.get(field) for field in fields} for row in (result.data or [])]
    return sorted(entries, key=lambda row: (
        str(row.get("run_date") or ""), str(row.get("time") or ""), str(row.get("id") or ""),
    ))


def _get_scheduler_job(post_id: int) -> dict | None:
    result = (
        supabase.table("schedulers").select("id,trigger,run_date")
        .eq("post_id", post_id).limit(1).maybe_single().execute()
    )
    return result.data if result else None


def _is_scheduled(job: dict | None, post: dict) -> bool:
    return job is not None and not post.get("publish_immediately", False)


async def _create_schedule_jobs(user_id: int, post_id: int, func: str, schedule: PostSchedule, profile_id: str) -> None:
    created: list[str] = []
    try:
        for time in schedule.times or [schedule.time]:
            job_id = await create_scheduler_job(
                user_id=user_id, post_id=post_id, func=func, trigger=schedule.trigger,
                time=time, day_of_week=schedule.day_of_week,
                days_of_week=schedule.days_of_week, start_date=schedule.start_date,
                run_date=schedule.run_date, profile_id=profile_id,
            )
            created.append(job_id)
    except Exception as exc:
        # A causa técnica fica no log, sem expor dados ou segredos ao usuário.
        logger.error(
            "Falha ao registrar agenda: func=%s post_id=%s jobs_criados=%s tipo=%s detalhe=%s",
            func, post_id, len(created), type(exc).__name__,
            str(exc) if isinstance(exc, InternalApiError) else "erro interno",
        )
        for job_id in created:
            try:
                await remove_scheduler_job(user_id, job_id)
            except Exception:
                logger.error("Falha ao desfazer job recorrente %s", job_id, exc_info=True)
        raise


# activity_types (migração 005): 1=bot_post_success, 2=bot_post_failure —
# gravados pelos bots do scheduler (Flask) e pelo listener de erro/missed.
_PUBLISH_ACTIVITY_STATUS = {1: "published", 2: "failed"}


MANUAL_CONFIRMATION_PREFIX = "MANUAL_CONFIRMED; "
USER_REPORTED_REMOVED_PREFIX = "USER_REPORTED_REMOVED; "
MANUAL_RETRY_PREFIX = "MANUAL_RETRY_REQUESTED; "


def _utc_instant(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _latest_publish_job(user_id: int, post_id: int, profile_id: str | None = None) -> dict | None:
    """Última ocorrência de fila, sempre isolada pelo dono e perfil."""
    result = (
        scope_owner(supabase.table("publish_jobs").select(
            "id,scheduler_id,status,idempotency_key,created_at,started_at,finished_at,last_error,external_id"
        ), user_id, profile_id)
        .eq("post_id", post_id)
        .order("created_at", desc=True)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return (result.data or [None])[0]


def _post_admin_access(user_id: int) -> bool:
    """Nunca confia no papel enviado pelo navegador."""
    try:
        row = (supabase.table("users").select("access")
               .eq("id", user_id).maybe_single().execute())
        return (row.data or {}).get("access") == "ADMIN"
    except Exception:
        logger.warning("Não foi possível consultar papel do usuário %s", user_id, exc_info=True)
        return False


def _public_publish_result(result: dict | None, is_admin: bool) -> dict | None:
    if not result or is_admin:
        return result
    # Dados brutos da Meta e textos técnicos ficam restritos ao administrador.
    return {**result, "error": (
        "Falha parcial na publicação. Confira o post na rede antes de tentar novamente."
        if result.get("partial_failure") else
        "Falha ao publicar. Confira o horário da execução."
        if result.get("status") == "failed" else
        result.get("error") if result.get("status") == "unknown" else None
    )}


def _last_successful_post_at(user_id: int, post_id: int, profile_id: str | None) -> str | None:
    """Última postagem confirmada; nunca usa erro ou tentativa como publicação."""
    latest: list[str] = []
    try:
        jobs = (scope_owner(
            supabase.table("publish_jobs").select("finished_at,started_at,created_at"),
            user_id, profile_id
        ).eq("post_id", post_id).eq("status", "succeeded")
         .order("finished_at", desc=True).limit(1).execute().data or [])
        if jobs:
            latest.append(jobs[0].get("finished_at") or jobs[0].get("started_at") or jobs[0]["created_at"])
    except Exception:
        logger.warning("Falha ao consultar a última publicação confirmada de %s", post_id, exc_info=True)
    try:
        activities = (scope_owner(
            supabase.table("activities").select("created_at"), user_id, profile_id
        ).eq("activity_id", 1).eq("metadata->>post_id", str(post_id))
         .order("created_at", desc=True).limit(1).execute().data or [])
        if activities:
            latest.append(activities[0]["created_at"])
    except Exception:
        logger.warning("Falha ao consultar histórico publicado de %s", post_id, exc_info=True)
    latest.sort(key=lambda value: _utc_instant(value) or datetime.min.replace(tzinfo=timezone.utc))
    return latest[-1] if latest else None


def _legacy_container_error_parts(activity: dict | None, job: dict) -> int | None:
    """Evidência de 4xx ao criar mídia, ligada à ocorrência e ao número já enviado.

    O erro na parte 2 não significa que a parte 1 falhou. A fila continua
    unknown para impedir reenvio duplicado; só a apresentação sinaliza
    a falha parcial no horário correto.
    """
    if not activity or activity.get("activity_id") != 2 or job.get("status") != "unknown":
        return None
    metadata = activity.get("metadata") or {}
    try:
        published_parts = int(metadata.get("published_parts"))
    except (TypeError, ValueError):
        return None
    if published_parts < 0 or str(metadata.get("job_id")) != str(job.get("scheduler_id")):
        return None
    error = str(metadata.get("error") or "")
    if not re.search(
        r"Failed to Create (?:Media Container|Carousel Item|Carousel Container).*?(?:Status:|HTTP)\s*4\d\d",
        error, re.IGNORECASE | re.DOTALL,
    ):
        return None
    event_time = _utc_instant(activity.get("created_at"))
    finish_time = _utc_instant(job.get("finished_at") or job.get("started_at"))
    if not event_time or not finish_time or abs((event_time - finish_time).total_seconds()) > 300:
        return None
    return published_parts


def _confirmed_legacy_container_rejection(activity: dict | None, job: dict) -> bool:
    """Primeiro contêiner recusado: falha confirmada sem partes publicadas."""
    return _legacy_container_error_parts(activity, job) == 0


def _schedule_slot_history(
    user_id: int, post_id: int, profile_id: str | None,
    entries: list[dict], is_admin: bool,
) -> list[dict]:
    """Uma linha por dia/hora configurado com última ocorrência real.
    A chave cron salva o minuto LOCAL da execução; nunca inferimos sucesso
    a partir do scheduler ou do horário previsto.
    """
    if not entries:
        return []
    latest_by_slot: dict[tuple[int | None, str, str], dict] = {}
    try:
        jobs = (scope_owner(
            supabase.table("publish_jobs").select(
                "scheduler_id,idempotency_key,status,created_at,started_at,finished_at,last_error"
            ), user_id, profile_id
        ).eq("post_id", post_id).order("created_at", desc=True)
         .limit(500).execute().data or [])
    except Exception:
        logger.warning("Falha ao obter ocorrências do post %s", post_id, exc_info=True)
        jobs = []

    legacy_rejections: list[dict] = []
    if any(job.get("status") == "unknown" for job in jobs):
        try:
            legacy_rejections = (scope_owner(
                supabase.table("activities").select("activity_id,metadata,created_at"),
                user_id, profile_id
            ).eq("activity_id", 2).eq("metadata->>post_id", str(post_id))
             .order("created_at", desc=True).limit(500).execute().data or [])
        except Exception:
            logger.warning("Falha ao consultar erros legados do post %s", post_id, exc_info=True)

    def slot_state(job: dict | None) -> str:
        if not job:
            return "programado"
        for row in legacy_rejections:
            parts = _legacy_container_error_parts(row, job)
            if parts is not None:
                return "erro" if parts == 0 else "erro parcial"
        return {
            "succeeded": "postado", "failed": "erro",
            "pending": "programado", "running": "em execução",
            "unknown": "sem confirmação",
        }.get(job.get("status"), "sem confirmação")

    for job in jobs:
        scheduler_id = str(job.get("scheduler_id") or "")
        key = str(job.get("idempotency_key") or "")
        day: int | None = None
        time_value = ""
        if ":" in key:
            try:
                occurrence = datetime.strptime(key.split(":", 1)[1], "%Y-%m-%dT%H:%M")
                day = occurrence.weekday()
                time_value = occurrence.strftime("%H:%M")
            except ValueError:
                continue
        else:
            # Ocorrências date antigas (um único horário sem dia da semana).
            matching = next((entry for entry in entries if str(entry["id"]) == scheduler_id), None)
            if not matching or matching.get("trigger") != "date":
                continue
            time_value = str(matching.get("run_date") or "")
        slot_key = (day, time_value, scheduler_id)
        latest_by_slot.setdefault(slot_key, job)

    slots = []
    for entry in entries:
        scheduler_id = str(entry["id"])
        if entry.get("trigger") == "cron":
            days = entry.get("days_of_week") or [entry.get("day_of_week")]
            time_value = str(entry.get("time") or "")[:5]
            for day in days:
                if day is None:
                    continue
                job = latest_by_slot.get((int(day), time_value, scheduler_id))
                slots.append({
                    "day_of_week": int(day), "time": time_value,
                    "status": slot_state(job),
                    "last_at": (job.get("finished_at") or job.get("started_at") or job.get("created_at")) if job else None,
                    "error": sanitize_log_data(str(job.get("last_error")))[:200]
                    if is_admin and job and slot_state(job) in ("erro", "erro parcial") and job.get("last_error") else None,
                })
        else:
            job = latest_by_slot.get((None, str(entry.get("run_date") or ""), scheduler_id))
            slots.append({
                "day_of_week": None, "time": str(entry.get("run_date") or ""),
                "status": slot_state(job),
                "last_at": (job.get("finished_at") or job.get("started_at") or job.get("created_at")) if job else None,
                "error": sanitize_log_data(str(job.get("last_error")))[:200]
                if is_admin and job and slot_state(job) in ("erro", "erro parcial") and job.get("last_error") else None,
            })
    return sorted(slots, key=lambda item: (item["day_of_week"] if item["day_of_week"] is not None else 7, item["time"]))



def _require_legacy_post_origin(post: dict) -> None:
    """Campanhas são controladas somente pela máquina de estados de campanha."""
    if post.get("publication_origin", "legacy") == "campaign":
        raise HTTPException(status_code=409, detail="Esta publicação pertence a uma campanha. Use os controles da campanha.")


def _ensure_post_editable(user_id: int, post_id: int, profile_id: str | None, post: dict) -> None:
    """Proíbe edições que alterariam uma publicação já programada ou enviada."""
    _require_legacy_post_origin(post)
    detail = "Este post já foi publicado ou está programado. Não é possível editar seu conteúdo ou suas mídias."
    if post.get("publish_immediately") or _get_post_schedule_entries(user_id, post_id):
        raise HTTPException(status_code=409, detail=detail)
    queued = (
        scope_owner(supabase.table("publish_jobs").select("id"), user_id, profile_id)
        .eq("post_id", post_id).execute()
    )
    if queued.data:
        raise HTTPException(status_code=409, detail=detail)
    activities = (
        scope_owner(supabase.table("activities").select("activity_id"), user_id, profile_id)
        .eq("metadata->>post_id", str(post_id)).execute()
    )
    if any(row.get("activity_id") in _PUBLISH_ACTIVITY_STATUS for row in (activities.data or [])):
        raise HTTPException(status_code=409, detail=detail)


def _get_last_publish_result(
    user_id: int, post_id: int, profile_id: str | None = None
) -> dict | None:
    """Une eventos e estado da fila; 'unknown' não pode parecer agendado."""
    job = None
    try:
        job = _latest_publish_job(user_id, post_id, profile_id)
    except Exception:
        logger.warning("Falha ao consultar fila do post %s", post_id, exc_info=True)

    activity = None
    try:
        query = supabase.table("activities").select("activity_id, metadata, created_at")
        query = scope_owner(query, user_id, profile_id)
        rows = (query.in_("activity_id", list(_PUBLISH_ACTIVITY_STATUS))
                .eq("metadata->>post_id", str(post_id))
                .order("created_at", desc=True).limit(1).execute().data or [])
        activity = rows[0] if rows else None
    except Exception:
        logger.warning("Falha ao ler resultado de publicação do post %s", post_id, exc_info=True)

    return _resolve_last_publish_result(job, activity)


def _resolve_last_publish_result(job: dict | None, activity: dict | None) -> dict | None:
    """Regra única (sem acesso ao banco) usada pela consulta individual e pela listagem em lote."""
    if job:
        published_parts = _legacy_container_error_parts(activity, job)
        if published_parts is not None:
            error = (activity.get("metadata") or {}).get("error")
            result = {
                "status": "failed" if published_parts == 0 else "unknown",
                "at": activity.get("created_at"),
                "error": sanitize_log_data(str(error))[:200] if error else None,
            }
            if published_parts > 0:
                result.update({"partial_failure": True, "job_id": job.get("id")})
            return result

    if activity and (not job or (
        (_utc_instant(activity.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc))
        >= (_utc_instant(job.get("finished_at") or job.get("started_at") or job.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc))
    )):
        error = (activity.get("metadata") or {}).get("error")
        return {
            "status": _PUBLISH_ACTIVITY_STATUS.get(activity.get("activity_id")),
            "at": activity.get("created_at"),
            "error": sanitize_log_data(str(error))[:200] if error else None,
        }
    if not job:
        return None
    if job["status"] == "pending":
        if str(job.get("idempotency_key") or "").startswith("manual_retry:"):
            return {"status": "retry_pending", "at": job.get("created_at"), "error": None}
        return None

    state = job["status"]
    manual = state == "succeeded" and (job.get("last_error") or "").startswith(MANUAL_CONFIRMATION_PREFIX)
    reported_removed = state == "unknown" and (job.get("last_error") or "").startswith(USER_REPORTED_REMOVED_PREFIX)
    status_label = (
        "manual_confirmed" if manual else
        "reported_removed" if reported_removed else
        {"succeeded": "published", "failed": "failed", "unknown": "unknown",
         "running": "running"}.get(state)
    )
    return {
        "status": status_label,
        "at": job.get("finished_at") or job.get("started_at"),
        "error": (
            "Execução sem confirmação. Confira na rede antes de agir."
            if state == "unknown" and not reported_removed else
            sanitize_log_data(str(job.get("last_error")))[:200] if state == "failed" and job.get("last_error")
            else None
        ),
        **({"proof_url": job.get("external_id")} if manual else {}),
        **({"job_id": job["id"]} if state == "unknown" and not reported_removed else {}),
    }


def _valid_threads_permalink(value: str) -> str | None:
    """Aceita somente permalink de publicação Threads sem query/fragmento."""
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        return None
    if (parsed.hostname or "").lower() not in ("threads.com", "www.threads.com", "threads.net", "www.threads.net"):
        return None
    if parsed.query or parsed.fragment:
        return None
    if not re.fullmatch(r"/@[A-Za-z0-9_.]{1,30}/post/[A-Za-z0-9_-]{4,70}/?", parsed.path):
        return None
    return "https://" + parsed.hostname.lower() + parsed.path.rstrip("/")


class ReconcilePostBody(BaseModel):
    permalink: str | None = None
    confirmed: bool = False
    reported_removed: bool = False


@router.post("/{post_id}/reconcile", status_code=200)
def reconcile_post(
    post_id: int,
    body: ReconcilePostBody,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """O proprietário atesta manualmente a publicação sem dispará-la novamente.

    O histórico da falha anterior permanece em last_error; o status succeeded
    é distinguível via marcador e URL da evidência. O endpoint não consulta
    nem assume validação automática pela Meta.
    """
    post = _get_post(user_id, post_id, profile_id)
    _require_legacy_post_origin(post)
    if post.get("network") != "threads":
        raise HTTPException(status_code=422, detail="Conciliação manual disponível apenas para Threads")
    if body.confirmed is not True:
        raise HTTPException(status_code=422, detail="Confirme a informação de forma explícita")
    if body.reported_removed:
        # A self-reported outcome without an external permalink is NOT a Meta-confirmed success.
        # Keep the queue status unknown to preserve idempotency and block republishing.
        if body.permalink:
            raise HTTPException(status_code=422, detail="Não forneça link no relato de publicação já removida")
        job = _latest_publish_job(user_id, post_id, profile_id)
        if not job or job.get("status") != "unknown" or (
            job.get("last_error") or "").startswith((USER_REPORTED_REMOVED_PREFIX, MANUAL_RETRY_PREFIX)):
            raise HTTPException(status_code=409, detail="Esta execução já foi tratada ou mudou de estado")
        old_error = sanitize_log_data(str(job.get("last_error") or ""))[:180]
        event = f"{USER_REPORTED_REMOVED_PREFIX}user={user_id}; original={old_error}"
        try:
            response = (
                scope_owner(
                    supabase.table("publish_jobs").update({"last_error": event}),
                    user_id, profile_id,
                )
                .eq("id", job["id"]).eq("post_id", post_id)
                .eq("status", "unknown").eq("last_error", job.get("last_error"))
                .execute()
            )
        except Exception:
            logger.exception("Falha ao registrar relato de publicação removida %s", post_id)
            raise HTTPException(status_code=503, detail="Não foi possível registrar o relato")
        if not response.data:
            raise HTTPException(status_code=409, detail="A execução mudou de estado. Atualize a lista.")
        log_action(
            "post_user_reported_published_removed",
            f"post_id={post_id} job_id={job['id']} original_status=unknown evidence=unavailable",
            user_id=user_id, profile_id=profile_id,
        )
        return {"status": "reported_removed",
                "msg": "Relato registrado. Sem confirmação externa, sem reenvio e com erro original preservado."}

    url = _valid_threads_permalink(body.permalink or "")
    if not url:
        raise HTTPException(status_code=422, detail="Forneça o link direto HTTPS da publicação no Threads")

    job = _latest_publish_job(user_id, post_id, profile_id)
    if not job or job.get("status") != "unknown" or (
        job.get("last_error") or "").startswith((USER_REPORTED_REMOVED_PREFIX, MANUAL_RETRY_PREFIX)):
        raise HTTPException(status_code=409, detail="A publicação não está pendente de conciliação")
    old_error = sanitize_log_data(str(job.get("last_error") or ""))[:180]
    event = f"{MANUAL_CONFIRMATION_PREFIX}user={user_id}; original={old_error}"
    try:
        response = (
            scope_owner(
                supabase.table("publish_jobs").update({
                    "status": "succeeded", "external_id": url,
                    "last_error": event,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }), user_id, profile_id
            )
            .eq("id", job["id"]).eq("post_id", post_id).eq("status", "unknown")
            .eq("last_error", job.get("last_error"))
            .execute()
        )
    except Exception:
        logger.exception("Falha ao conciliar publicação %s", post_id)
        raise HTTPException(status_code=503, detail="Não foi possível registrar a confirmação")
    if not response.data:
        raise HTTPException(status_code=409, detail="A publicação mudou de estado. Atualize a lista.")

    log_action(
        "post_manual_reconciliation",
        f"post_id={post_id} job_id={job['id']} original_status=unknown evidence_url={url}",
        user_id=user_id, profile_id=profile_id,
    )
    return {"status": "manual_confirmed", "proof_url": url,
            "msg": "Confirmado por você com o link fornecido, sem reenviar o post."}




class RetryUnknownPostBody(BaseModel):
    source_job_id: uuid.UUID
    confirmed_not_published: bool = False
    accepts_duplicate_risk: bool = False


@router.post("/{post_id}/retry-unknown", status_code=202)
def retry_unknown_post(
    post_id: int,
    body: RetryUnknownPostBody,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Enfileira nova ocorrência após conferência manual explícita.

    RPC faz transição e INSERT numa transação com lock na ocorrência
    original. Nunca reusa idempotency key antiga, nem publica nesta request.
    """
    profile_id = _require_profile_id(profile_id)
    post = _get_post(user_id, post_id, profile_id)
    _require_legacy_post_origin(post)
    if (post.get("network") or "threads") != "threads":
        raise HTTPException(status_code=422, detail="Reenvio manual disponível apenas para Threads")
    if body.confirmed_not_published is not True or body.accepts_duplicate_risk is not True:
        raise HTTPException(
            status_code=422,
            detail="Confira a conta do Threads e aceite explicitamente o risco de publicação duplicada.",
        )

    _check_network_rules(
        "threads", [row.get("text") or "" for row in _get_thread_chain(post_id, user_id)],
        _get_post_medias(post_id), len(_get_post_products(post_id)),
        check_required_media=True,
    )
    latest = _latest_publish_job(user_id, post_id, profile_id)
    if not latest or latest.get("status") != "unknown" or str(latest["id"]) != str(body.source_job_id):
        raise HTTPException(status_code=409, detail="O estado da publicação mudou. Atualize a lista.")
    if (latest.get("last_error") or "").startswith(
        (USER_REPORTED_REMOVED_PREFIX, MANUAL_RETRY_PREFIX)
    ):
        raise HTTPException(status_code=409, detail="Esta execução já foi tratada.")

    try:
        result = supabase.rpc("enqueue_manual_post_retry", {
            "p_user_id": user_id,
            "p_profile_id": profile_id,
            "p_post_id": post_id,
            "p_source_job_id": str(body.source_job_id),
        }).execute()
    except Exception:
        logger.exception("Falha ao registrar reenvio manual do post %s", post_id)
        raise HTTPException(status_code=503, detail="Não foi possível colocar o reenvio na fila.")
    if not result.data:
        raise HTTPException(status_code=409, detail="O estado da publicação mudou. Atualize a lista.")

    log_action(
        "post_manual_retry_requested",
        f"post_id={post_id} previous_job={body.source_job_id} retry_job={result.data} network=threads",
        user_id=user_id, profile_id=profile_id,
    )
    return {"status": "queued", "msg": "Reenvio colocado na fila. O resultado aparecerá no post em instantes."}



def _get_thread_chain(head_id: int, user_id: int) -> list[dict]:
    """Head primeiro, depois cada parte seguinte (post_id aponta pra
    parte ANTERIOR — ver docstring do módulo). Bounded por MAX_PARTS
    pra nunca entrar em loop infinito se o dado estiver corrompido.

    S-01: `user_id` é obrigatório; um head de outra conta responde 404 mesmo
    que um chamador futuro esqueça a verificação de dono."""
    MAX_PARTS = 50
    chain = [_get_post_by_id_only(head_id, user_id)]
    owner = chain[0]["user_id"]
    profile = chain[0].get("profile_id")
    current_id = head_id
    for _ in range(MAX_PARTS):
        query = (
            supabase.table("posts").select("*")
            .eq("post_id", current_id).eq("user_id", owner)
        )
        query = query.eq("profile_id", profile) if profile else query.is_("profile_id", "null")
        next_result = query.maybe_single().execute()
        if not next_result or not next_result.data:
            break
        chain.append(next_result.data)
        current_id = next_result.data["id"]
    return chain


def _get_post_by_id_only(post_id: int, user_id: int) -> dict:
    result = (
        supabase.table("posts").select("*")
        .eq("id", post_id).eq("user_id", user_id).single().execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")
    return result.data


def _create_thread(
    user_id: int, texts: list[str], network: str, profile_id: str,
    group_id: str | None = None,
    publish_immediately: bool = False,
) -> dict:
    """Insere a thread inteira, encadeando post_id. Retorna a head.

    `network` só é gravada na head (post_id IS NULL) — é lá que
    agendamento e produtos vivem, mesma simplificação já usada pro
    resto da thread (ver docstring do módulo)."""
    profile_id = _require_profile_id(profile_id)
    # As redes sem suporte a respostas encadeadas recebem apenas a legenda.
    # A decisão final é do servidor, mesmo para quem chama a API diretamente.
    from ..network_limits import NETWORK_RULES
    publishable_texts = texts if NETWORK_RULES[network]["thread_parts"] else texts[:1]
    parent_id = None
    head = None
    for text in publishable_texts:
        row_data = {"user_id": user_id, "text": text, "post_id": parent_id}
        row_data["profile_id"] = profile_id
        if parent_id is None:
            row_data["network"] = network
            row_data["publish_immediately"] = publish_immediately
            if group_id:  # só quando veio: sem a coluna (migração 044) nada muda
                row_data["group_id"] = group_id
        result = (
            supabase.table("posts")
            .insert(row_data)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Falha ao criar post")
        row = result.data[0]
        if head is None:
            head = row
        parent_id = row["id"]
    return head


def _delete_thread_cascade(head_id: int, user_id: int) -> None:
    """Apaga a thread inteira (head + partes) + associações de produto
    e mídia (arquivo em disco + linhas). Usado no DELETE e pra desfazer
    a criação se o agendamento falhar."""
    chain = _get_thread_chain(head_id, user_id)

    media_rows = (
        supabase.table("posts_medias")
        .select("medias(id, file_path)")
        .eq("post_id", head_id)
        .execute()
    )
    for item in media_rows.data or []:
        media = item.get("medias")
        if media and _media_shared_elsewhere(media["id"], head_id):
            continue  # outro post do grupo ainda usa: só o vínculo sai
        if media and media.get("file_path"):
            _remove_media_file(media["file_path"])
        if media:
            supabase.table("medias").delete().eq("id", media["id"]).execute()

    supabase.table("posts_medias").delete().eq("post_id", head_id).execute()
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
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Gera texto via credencial da plataforma, sem chave por cliente.

    Com `networks`, devolve uma descrição por rede em uma geração;
    `text` mantém a primeira descrição para compatibilidade."""
    from apis import llm
    from .platform_ai import resolve_platform_ai_key

    # Cada chamada custa uma requisição paga de LLM: limite por usuário.
    _check_login_rate_limit(
        f"generate-copy:{user_id}",
        detail="Muitas gerações de texto em pouco tempo. Aguarde um minuto.",
    )

    product_result = (
        scope_account(
            supabase.table("products").select("*").eq("id", body.product_id),
            user_id,
        )
        .single()
        .execute()
    )
    if not product_result.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Nunca entregar ao LLM o offerLink antigo da conta ADMIN. O texto de
    # divulgação deve conter o link do afiliado desta conta, inclusive para
    # produtos que já existiam antes da troca para a API global.
    from .platform_shopee import get_affiliate_id
    from ..shopee_affiliate_links import canonical_product_url, personalize_product
    product_for_copy = product_result.data
    if canonical_product_url(product_for_copy.get("original_link")):
        affiliate_id = get_affiliate_id(user_id)
        if not affiliate_id:
            raise HTTPException(status_code=400, detail="Cadastre seu ID de afiliado Shopee antes de gerar textos.")
        product_for_copy = personalize_product(product_for_copy, affiliate_id)

    provider, api_key, model = resolve_platform_ai_key()

    def complete(prompt: str, max_tokens: int) -> str:
        return llm.complete(provider, api_key, model, prompt, max_tokens)

    def generate():
        if body.description_only:
            return [], [generate_short_product_description(product_for_copy, body.persona, complete)]
        if body.mode == "append":
            replies = generate_thread_replies(
                product_for_copy, body.persona, body.networks,
                body.existing_texts,
                body.part_count - len(body.existing_texts), complete,
            )
            return [], replies

        variants = generate_variants(
            product_for_copy, body.persona, body.networks, complete,
        )
        # Threads/X may receive a shorter head variant than Facebook/Instagram.
        # Continue the actual thread head, not the longest generic description.
        thread_variant = next(
            (v for v in variants if any(n in v["networks"] for n in ("threads", "x"))),
            variants[0],
        )
        replies = generate_thread_replies(
            product_for_copy, body.persona, body.networks,
            [thread_variant["text"]], body.part_count - 1, complete,
        )
        return variants, replies

    try:
        variants, replies = await run_in_threadpool(generate)
    except llm.LLMError as e:
        logger.warning("Falha ao gerar texto do produto %s (%s): %s", body.product_id, provider, e.kind)
        raise HTTPException(status_code=400, detail=str(e))

    if body.description_only:
        return {"text": replies[0], "variants": [], "parts": replies, "start_index": 0}
    if body.mode == "append":
        return {
            "text": body.existing_texts[0], "variants": [],
            "parts": replies, "start_index": len(body.existing_texts),
        }
    return {
        "text": variants[0]["text"], "variants": variants,
        "parts": [variants[0]["text"], *replies], "start_index": 0,
    }


# --- Listagem em lote -------------------------------------------------------------
# A listagem não pode consultar o banco post a post (~9 consultas por post). Estas funções buscam
# tudo da página com `IN (...)` e montam o mesmo resultado das funções individuais acima
# (a equivalência é testada em tests/api/test_posts_list_batch.py).
_LIST_ID_CHUNK = 15
_LIST_ROW_LIMIT = 1000


def _id_chunks(ids: list[int], size: int = _LIST_ID_CHUNK):
    for start in range(0, len(ids), size):
        yield ids[start:start + size]


def _batch_schedule_entries(user_id: int, ids: list[int]) -> dict[int, list[dict]]:
    fields = ("id", "trigger", "run_date", "time", "day_of_week", "days_of_week", "start_date")
    grouped: dict[int, list[dict]] = {}
    for chunk in _id_chunks(ids):
        rows = (
            supabase.table("schedulers").select(",".join(("post_id",) + fields))
            .eq("user_id", user_id).in_("post_id", chunk).limit(_LIST_ROW_LIMIT).execute().data or []
        )
        for row in rows:
            grouped.setdefault(row["post_id"], []).append({field: row.get(field) for field in fields})
    return {
        post_id: sorted(entries, key=lambda row: (
            str(row.get("run_date") or ""), str(row.get("time") or ""), str(row.get("id") or ""),
        )) for post_id, entries in grouped.items()
    }


def _batch_thread_chains(heads: list[dict], user_id: int) -> dict[int, list[dict]]:
    """Cabeça + partes seguintes de cada thread, uma consulta por nível (normalmente 1 no total).

    Igual a `_get_thread_chain`: cada parte aponta para a anterior (`post_id`) e herda dono e perfil
    da cabeça. Limitado a 50 partes para nunca entrar em loop com dado corrompido."""
    chains = {head["id"]: [head] for head in heads}
    tails = {head["id"]: head for head in heads}  # id da última parte conhecida -> cabeça da thread
    for _ in range(50):
        if not tails:
            break
        found: dict[int, dict] = {}
        for chunk in _id_chunks(list(tails)):
            rows = (
                supabase.table("posts").select("*")
                .eq("user_id", user_id).in_("post_id", chunk)
                .order("id").limit(_LIST_ROW_LIMIT).execute().data or []
            )
            for row in rows:
                head = tails[row["post_id"]]
                if row["post_id"] in found or row.get("profile_id") != head.get("profile_id"):
                    continue
                found[row["post_id"]] = row
        next_tails: dict[int, dict] = {}
        for parent_id, row in found.items():
            head = tails[parent_id]
            chains[head["id"]].append(row)
            next_tails[row["id"]] = head
        tails = next_tails
    return chains


def _batch_relations(table: str, select: str, key: str, ids: list[int]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for chunk in _id_chunks(ids):
        rows = (
            supabase.table(table).select(f"post_id, {select}")
            .in_("post_id", chunk).order("display_order").limit(_LIST_ROW_LIMIT).execute().data or []
        )
        for row in rows:
            if row.get(key):
                grouped.setdefault(row["post_id"], []).append(row[key])
    return grouped


_PRODUCT_FIELDS = "id, product_id, name, image, price_min, price_max, commission"
_MEDIA_FIELDS = "id, file_name, size, type"


def _batch_publish_state(user_id: int, profile_id: str | None, ids: list[int]) -> dict[str, dict[int, dict]]:
    """Última fila, último evento de publicação, último sucesso na fila e último evento de sucesso."""
    out: dict[str, dict[int, dict]] = {"job": {}, "job_ok": {}, "activity": {}, "activity_ok": {}}
    job_fields = "post_id,id,scheduler_id,status,idempotency_key,created_at,started_at,finished_at,last_error,external_id"
    for chunk in _id_chunks(ids):
        try:
            rows = (scope_owner(supabase.table("publish_jobs").select(job_fields), user_id, profile_id)
                    .in_("post_id", chunk).order("created_at", desc=True).order("id", desc=True)
                    .limit(_LIST_ROW_LIMIT).execute().data or [])
            for row in rows:
                out["job"].setdefault(row["post_id"], row)
        except Exception:
            logger.warning("Falha ao consultar a fila dos posts da página", exc_info=True)
        try:
            rows = (scope_owner(supabase.table("publish_jobs").select("post_id,finished_at,started_at,created_at"),
                                user_id, profile_id)
                    .in_("post_id", chunk).eq("status", "succeeded").order("finished_at", desc=True)
                    .limit(_LIST_ROW_LIMIT).execute().data or [])
            for row in rows:
                out["job_ok"].setdefault(row["post_id"], row)
        except Exception:
            logger.warning("Falha ao consultar publicações confirmadas da página", exc_info=True)
        wanted = [str(i) for i in chunk]
        for key, ids_filter in (("activity", list(_PUBLISH_ACTIVITY_STATUS)), ("activity_ok", [1])):
            try:
                rows = (scope_owner(supabase.table("activities").select("activity_id, metadata, created_at"),
                                    user_id, profile_id)
                        .in_("activity_id", ids_filter).in_("metadata->>post_id", wanted)
                        .order("created_at", desc=True).limit(_LIST_ROW_LIMIT).execute().data or [])
                for row in rows:
                    post_id = (row.get("metadata") or {}).get("post_id")
                    try:
                        post_id = int(post_id)
                    except (TypeError, ValueError):
                        continue
                    out[key].setdefault(post_id, row)
            except Exception:
                logger.warning("Falha ao ler eventos de publicação da página", exc_info=True)
    return out


def _enrich_listed_posts(rows: list[dict], user_id: int, profile_id: str | None, is_admin: bool) -> list[dict]:
    ids = [row["id"] for row in rows]
    if not ids:
        return []
    schedules = _batch_schedule_entries(user_id, ids)
    chains = _batch_thread_chains(rows, user_id)
    products = _batch_relations("posts_products", f"display_order, products({_PRODUCT_FIELDS})", "products", ids)
    medias = _batch_relations("posts_medias", f"display_order, medias({_MEDIA_FIELDS})", "medias", ids)
    state = _batch_publish_state(user_id, profile_id, ids)
    floor = datetime.min.replace(tzinfo=timezone.utc)

    posts: list[dict] = []
    for item in rows:
        post_id = item["id"]
        entries = schedules.get(post_id, [])
        job = entries[0] if entries else None
        chain = chains.get(post_id, [item])
        latest: list[str] = []
        ok_job = state["job_ok"].get(post_id)
        if ok_job:
            latest.append(ok_job.get("finished_at") or ok_job.get("started_at") or ok_job["created_at"])
        ok_activity = state["activity_ok"].get(post_id)
        if ok_activity:
            latest.append(ok_activity["created_at"])
        latest.sort(key=lambda value: _utc_instant(value) or floor)
        result = _resolve_last_publish_result(state["job"].get(post_id), state["activity"].get(post_id))
        posts.append({
            **item,
            "texts": [row["text"] for row in chain],
            "products": products.get(post_id, []),
            "medias": medias.get(post_id, []),
            "scheduled": _is_scheduled(job, item),
            "schedule_trigger": job.get("trigger") if job else None,
            "schedule_entries": entries,
            "scheduled_for": job.get("run_date") if job and job.get("trigger") == "date" else None,
            "parts_count": len(chain),
            "last_result": _public_publish_result(result, is_admin),
            "last_published_at": latest[-1] if latest else None,
        })
    return posts


def _enrich_listed_post(item: dict, user_id: int, profile_id: str | None, is_admin: bool) -> dict:
    """Versão individual (referência de comportamento): os testes comparam o lote com ela."""
    schedule_entries = _get_post_schedule_entries(user_id, item["id"])
    job = schedule_entries[0] if schedule_entries else None
    chain = _get_thread_chain(item["id"], user_id)
    return {
        **item,
        "texts": [row["text"] for row in chain],
        "products": _get_post_products(item["id"]),
        "medias": _get_post_medias(item["id"]),
        "scheduled": _is_scheduled(job, item),
        "schedule_trigger": job.get("trigger") if job else None,
        "schedule_entries": schedule_entries,
        "scheduled_for": (
            job.get("run_date")
            if job and job.get("trigger") == "date"
            else None
        ),
        "parts_count": len(chain),
        "last_result": _public_publish_result(
            _get_last_publish_result(user_id, item["id"], profile_id), is_admin
        ),
        "last_published_at": _last_successful_post_at(user_id, item["id"], profile_id),
    }


@router.get("")
async def list_posts(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    cursor: str | None = Query(None, description="Cursor de paginação (created_at)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Lista posts únicos (post_id IS NULL — sem thread) com paginação por cursor."""
    started = time.monotonic()
    query = (
        scope_owner(supabase.table("posts").select("*"), user_id, profile_id)
        .is_("post_id", "null")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)

    # O cliente do Supabase é síncrono: fora do event loop, para não parar a API inteira.
    result = await run_in_threadpool(query.execute)
    rows = result.data or []

    is_admin = await run_in_threadpool(_post_admin_access, user_id) if rows else False
    posts = await run_in_threadpool(_enrich_listed_posts, rows, user_id, profile_id, is_admin)

    next_cursor = None
    if rows and len(rows) == limit:
        next_cursor = rows[-1]["created_at"]

    elapsed = time.monotonic() - started
    if elapsed > 5:
        logger.warning("Listagem de posts lenta: %.1fs para %d posts (limit=%d)", elapsed, len(posts), limit)
    return {"data": posts, "next_cursor": next_cursor}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostCreate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Cria a thread (1+ partes, ver docstring do módulo) e agenda a
    publicação. Se o agendamento falhar, desfaz a criação inteira —
    melhor não criar do que criar um post que nunca vai publicar."""
    profile_id = _require_profile_id(profile_id)
    _check_network_enabled(body.network)
    _validate_product_ids(user_id, body.product_ids)
    medias = _get_owned_medias(user_id, body.media_ids, profile_id)
    _check_network_rules(body.network, body.texts, medias, len(body.product_ids))
    await _ensure_scheduler_available()
    head = _create_thread(
        user_id, body.texts, body.network, profile_id,
        str(body.group_id) if body.group_id else None,
    )
    _set_post_products(head["id"], body.product_ids)
    if medias:
        supabase.table("posts_medias").insert([
            {"post_id": head["id"], "media_id": m["id"], "display_order": i}
            for i, m in enumerate(medias)
        ]).execute()

    try:
        reserve_post_plan_quota(
            user_id, profile_id, head["id"], immediate=False,
            days=body.schedule.days_of_week, times=body.schedule.times,
        )
        await _create_schedule_jobs(user_id, head["id"], NETWORK_FUNC_MAP[body.network], body.schedule, profile_id)
    except HTTPException:
        _delete_thread_cascade(head["id"], user_id)
        raise
    except InternalApiError:
        _delete_thread_cascade(head["id"], user_id)
        raise HTTPException(
            status_code=502,
            detail="Não foi possível agendar a publicação agora. Post não foi criado.",
        )

    return {
        **head,
        "texts": body.texts,
        "products": _get_post_products(head["id"]),
        "medias": medias,
        "scheduled": True,
    }


def _x_media_allowed(user_id: int, profile_id: str) -> bool:
    """A conexão do X deste perfil tem `media.write`? Escopo NULL (conexão
    antiga) conta como não: o upload falharia só na hora de publicar."""
    row = (
        scope_owner(supabase.table("x_credentials").select("scope"), user_id, profile_id)
        .maybe_single().execute()
    )
    return x_oauth.has_media_write(row.data.get("scope") if row and row.data else None)


def _x_media_for(body: PostBatchCreate, user_id: int, profile_id: str) -> bool:
    """Só consulta o banco quando há X + mídia na composição."""
    wants_x_media = bool(body.draft_media_ids) and any(c.network == "x" for c in body.compositions)
    return _x_media_allowed(user_id, profile_id) if wants_x_media else True


def _preview_batch(
    body: PostBatchCreate, drafts: list[dict], x_media_allowed: bool = True,
) -> list[dict]:
    plans: list[dict] = []
    media = [
        {"id": str(draft["id"]), "file_name": draft["file_name"], "size": draft["size_bytes"]}
        for draft in drafts
    ]
    for composition in body.compositions:
        disabled_reason = is_network_disabled(composition.network)
        if disabled_reason:
            plans.append({
                "network": composition.network,
                "texts": composition.texts[:1],
                "mode": "blocked",
                "media_draft_ids": [],
                "warnings": [],
                "blocked_reason": disabled_reason,
                "dropped": [],
            })
            continue
        plan = plan_network_composition(
            composition.network,
            composition.texts,
            media,
            len(body.product_ids),
        )
        entry = {
            "network": composition.network,
            "texts": plan.text_variant,
            "mode": plan.mode,
            "media_draft_ids": [str(media_id) for media_id in plan.media_ids],
            "warnings": plan.warnings,
            "blocked_reason": plan.blocked_reason,
            "dropped": plan.dropped,
        }
        if composition.network == "x" and entry["media_draft_ids"] and not x_media_allowed:
            entry.update(
                mode="blocked", media_draft_ids=[],
                blocked_reason=x_oauth.MEDIA_RECONNECT_MESSAGE,
            )
        plans.append(entry)
    return plans


@router.get("/scheduler-status")
async def get_scheduler_status(
    _user_id: int = Depends(get_current_user_id),
):
    return {
        "available": await _scheduler_is_available(),
        "message": SCHEDULER_UNAVAILABLE_MESSAGE,
    }


@router.post("/preview")
async def preview_post_batch(
    body: PostBatchCreate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Calcula resultados por rede sem criar post, job ou vínculo de mídia."""
    profile_id = _require_profile_id(profile_id)
    _validate_product_ids(user_id, body.product_ids)
    drafts = _get_owned_ready_drafts(user_id, body.draft_media_ids, profile_id)
    return {"plans": _preview_batch(body, drafts, _x_media_for(body, user_id, profile_id))}


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def create_posts_batch(
    body: PostBatchCreate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Cria somente as redes entregáveis; falhas de uma não cancelam as outras."""
    profile_id = _require_profile_id(profile_id)
    _validate_product_ids(user_id, body.product_ids)
    await _ensure_scheduler_available()
    drafts = _get_owned_ready_drafts(user_id, body.draft_media_ids, profile_id)
    drafts_by_id = {str(draft["id"]): draft for draft in drafts}
    plans = _preview_batch(body, drafts, _x_media_for(body, user_id, profile_id))
    deliverable = [plan for plan in plans if plan["mode"] != "blocked"]
    if not deliverable:
        return {"group_id": None, "created": [], "blocked": plans}

    group_id = str(uuid.uuid4())
    materialized: dict[str, dict] = {}
    created: list[dict] = []
    blocked = [plan for plan in plans if plan["mode"] == "blocked"]
    for plan in deliverable:
        head = _create_thread(user_id, plan["texts"], plan["network"], profile_id, group_id, body.publish_immediately)
        fresh: dict[str, dict | None] = {}  # rascunhos consumidos só por este plano
        try:
            reserve_post_plan_quota(
                user_id, profile_id, head["id"], immediate=body.publish_immediately,
                days=body.schedule.days_of_week, times=body.schedule.times,
            )
            _set_post_products(head["id"], body.product_ids)
            medias = _attach_medias(
                head["id"], plan["media_draft_ids"], drafts_by_id, materialized, fresh,
                user_id, profile_id,
            )
            # job por último: sem mídia vinculada ele nunca existe
            await _create_schedule_jobs(user_id, head["id"], NETWORK_FUNC_MAP[plan["network"]], body.schedule, profile_id)
        except Exception as exc:
            if not isinstance(exc, (InternalApiError, _DraftUnavailable, HTTPException)):
                logger.warning("Falha ao montar post da rede %s", plan["network"], exc_info=True)
            _rollback_plan(head["id"], fresh, materialized, user_id, profile_id)
            if body.publish_immediately:
                release_failed_post_plan_quota(user_id, profile_id, head["id"])
            blocked.append({
                **plan,
                "mode": "blocked",
                "blocked_reason": _block_reason(exc),
            })
            continue
        created.append({
            "network": plan["network"],
            "post_id": head["id"],
            "mode": plan["mode"],
            "warnings": plan["warnings"],
            "medias": medias,
        })

    return {"group_id": group_id if created else None, "created": created, "blocked": blocked}


@router.post("/media-drafts", status_code=status.HTTP_201_CREATED)
async def upload_media_draft(
    file: UploadFile,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Armazena uma mídia privada antes de existir um post.

    A chave do Storage é gerada no servidor, pertence ao perfil ativo e vence
    em 24 horas. A Task 3 será a única responsável por consumi-la em posts.
    """
    profile_id = _require_profile_id(profile_id)
    cleanup_expired_media_drafts()
    content = await _read_media_content(file)

    media = await _sanitize_upload(file, content)
    return _store_sanitized_draft(media, user_id, profile_id)


def _store_sanitized_draft(media, user_id: int, profile_id: str) -> dict:
    """Persist one sanitized asset in the existing private draft pipeline."""
    content = media.content
    mime = media.mime_type
    if not mime:
        raise HTTPException(
            status_code=400,
            detail="Conteúdo do arquivo não corresponde a uma mídia permitida.",
        )

    upload_id = str(uuid.uuid4())
    suffix = media.extension
    storage_key = f"drafts/{user_id}/{profile_id}/{upload_id}{suffix}"
    expires_at = (datetime.now(timezone.utc) + MEDIA_DRAFT_TTL).isoformat()
    media_type = media.media_type
    create = (
        supabase.table("temporary_media_uploads")
        .insert({
            "id": upload_id,
            "user_id": user_id,
            "profile_id": profile_id,
            "storage_bucket": MEDIA_DRAFT_BUCKET,
            "storage_key": storage_key,
            "file_name": media.safe_filename,
            "mime_type": mime,
            "size_bytes": len(content),
            "media_type": media_type,
            "status": "uploading",
            "expires_at": expires_at,
        })
        .execute()
    )
    if not create.data:
        raise HTTPException(status_code=500, detail="Não foi possível preparar a mídia.")

    try:
        with storage_upload_reservation(len(content)):
            try:
                supabase.storage.from_(MEDIA_DRAFT_BUCKET).upload(
                    storage_key, content, {"content-type": mime, "upsert": "false"}
                )
            except Exception:
                logger.warning("Falha ao guardar rascunho de mídia", exc_info=True)
                raise HTTPException(status_code=502, detail="Não foi possível enviar a mídia agora. Tente novamente.")
    except Exception:
        supabase.table("temporary_media_uploads").delete().eq("id", upload_id).eq("status", "uploading").execute()
        raise

    updated = (
        supabase.table("temporary_media_uploads")
        .update({"status": "ready"})
        .eq("id", upload_id)
        .eq("user_id", user_id)
        .eq("profile_id", profile_id)
        .eq("status", "uploading")
        .execute()
    )
    if not updated.data:
        try:
            _remove_draft_from_storage({"storage_bucket": MEDIA_DRAFT_BUCKET, "storage_key": storage_key})
        except Exception:
            logger.warning("Falha ao desfazer upload de rascunho", exc_info=True)
        raise HTTPException(status_code=500, detail="Não foi possível preparar a mídia.")
    return _draft_response(updated.data[0])


def _normalize_shopee_photo_as_jpeg(media, product_id: int):
    """A product image from PNG/WEBP/GIF becomes a safe universal JPEG preview."""
    if media.mime_type == "image/jpeg":
        return media
    with Image.open(BytesIO(media.content)) as source:
        frame = source.convert("RGBA")
        background = Image.new("RGB", frame.size, (255, 255, 255))
        background.paste(frame, mask=frame.getchannel("A"))
        output = BytesIO()
        background.save(output, format="JPEG", quality=90, optimize=True)
    return sanitize_media_upload(
        output.getvalue(), filename="shopee-" + str(product_id) + ".jpg",
        content_type="image/jpeg", max_bytes=MAX_PRODUCT_IMAGE_BYTES,
    )


@router.post("/product-image-drafts/{product_id}", status_code=status.HTTP_201_CREATED)
async def import_product_image_draft(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Import a catalog product photo into the active profile's private storage.

    Products belong to the account (user_id), while media drafts remain scoped
    to user_id + profile_id. No arbitrary URL fetch or video import is allowed.
    """
    profile_id = _require_profile_id(profile_id)
    product = scope_account(
        supabase.table("products").select("id,image").eq("id", product_id),
        user_id,
    ).maybe_single().execute()
    row = product.data if product else None
    if not row:
        raise HTTPException(status_code=404, detail="Produto não encontrado nesta conta.")
    if not row.get("image"):
        raise HTTPException(status_code=400, detail="O produto não possui foto cadastrada.")
    content = await _download_shopee_image(row["image"])
    try:
        detected = detect_media_type(content)
        if detected.media_type != "IMAGE":
            raise MediaSanitizerError("a origem não contém uma imagem")
        media = await run_in_threadpool(
            sanitize_media_upload, content,
            filename="shopee-" + str(product_id) + detected.extension,
            content_type=detected.mime_type,
            max_bytes=MAX_PRODUCT_IMAGE_BYTES,
        )
        media = await run_in_threadpool(_normalize_shopee_photo_as_jpeg, media, product_id)
    except MediaSanitizerError as exc:
        raise HTTPException(status_code=415, detail="Imagem Shopee inválida ou incompatível.") from None
    cleanup_expired_media_drafts()
    return _store_sanitized_draft(media, user_id, profile_id)


@router.delete("/media-drafts/{media_id}")
async def delete_media_draft(
    media_id: str,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Cancela somente o rascunho privado do perfil ativo."""
    profile_id = _require_profile_id(profile_id)
    result = (
        scope_owner(
            supabase.table("temporary_media_uploads").select("*").eq("id", media_id),
            user_id,
            profile_id,
        )
        .eq("status", "ready")
        .maybe_single()
        .execute()
    )
    draft = result.data if result else None
    if not draft:
        raise HTTPException(status_code=404, detail="Rascunho de mídia não encontrado")
    try:
        _remove_draft_from_storage(draft)
    except Exception:
        logger.warning("Falha ao remover rascunho de mídia", exc_info=True)
        raise HTTPException(status_code=502, detail="Não foi possível remover a mídia agora. Tente novamente.")
    supabase.table("temporary_media_uploads").delete().eq("id", media_id).eq("user_id", user_id).eq("profile_id", profile_id).eq("status", "ready").execute()
    return {"msg": "Rascunho de mídia removido"}


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    post = _get_post(user_id, post_id, profile_id)
    schedule_entries = _get_post_schedule_entries(user_id, post_id)
    job = schedule_entries[0] if schedule_entries else None
    chain = _get_thread_chain(post_id, user_id)
    is_admin = _post_admin_access(user_id)
    return {
        **post,
        "texts": [row["text"] for row in chain],
        "products": _get_post_products(post_id),
        "medias": _get_post_medias(post_id),
        "scheduled": _is_scheduled(job, post),
        "schedule_trigger": job.get("trigger") if job else None,
        "schedule_entries": schedule_entries,
        "scheduled_for": job.get("run_date") if job and job.get("trigger") == "date" else None,
        "last_result": _public_publish_result(
            _get_last_publish_result(user_id, post_id, profile_id), is_admin
        ),
        "last_published_at": _last_successful_post_at(user_id, post_id, profile_id),
        "schedule_slots": _schedule_slot_history(
            user_id, post_id, profile_id, schedule_entries, is_admin
        ),
    }


def _latest_future_revision(user_id: int, post_id: int, profile_id: str | None):
    response = (
        scope_owner(
            supabase.table("post_content_revisions")
            .select("id,effective_after,snapshot")
            .eq("post_id", post_id)
            .contains("snapshot", {"environment": current_environment()}), user_id, profile_id,
        )
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    item = response.data[0]
    snapshot = item.get("snapshot") or {}
    return {
        "id": item["id"],
        "effective_after": item["effective_after"],
        "texts": snapshot.get("texts") or [],
    }


class PostFutureRevision(BaseModel):
    texts: list[str]
    product_ids: list[int] = []

    @field_validator("texts")
    @classmethod
    def _check_future_texts(cls, value: list[str]) -> list[str]:
        if not value or len(value) > MAX_THREAD_PARTS or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise ValueError("Informe textos válidos para a revisão futura")
        return value


def _revision_media_snapshot(user_id: int, post_id: int, profile_id: str) -> list[dict]:
    """Mantém as mídias originais no Storage, sem sobrescrever/vazar objetos."""
    links = (
        supabase.table("posts_medias")
        .select("media_id,display_order")
        .eq("post_id", post_id)
        .order("display_order")
        .execute()
    )
    ids = [item["media_id"] for item in (links.data or [])]
    if not ids:
        return []
    rows = (
        scope_owner(
            supabase.table("medias").select("id,file_name,file_path,size,type"),
            user_id, profile_id,
        )
        .in_("id", ids)
        .execute()
    )
    found = {row["id"]: row for row in (rows.data or [])}
    if len(found) != len(set(ids)):
        raise HTTPException(status_code=409, detail="Mídia do post indisponível para revisão")
    return [found[media_id] for media_id in ids]


def _has_revision_schedule_in_environment(
    user_id: int, post_id: int, profile_id: str, environment: str,
) -> bool:
    """Nunca criar revisão de staging para uma agenda apenas da produção."""
    result = (
        scope_owner(
            supabase.table("schedulers").select("id").eq("post_id", post_id)
            .eq("environment", environment).is_("dispatch_cancelled_at", "null"),
            user_id, profile_id,
        )
        .limit(1)
        .execute()
    )
    return bool(result.data)


@router.post("/{post_id}/future-revisions", status_code=status.HTTP_201_CREATED)
def create_future_revision(
    post_id: int,
    body: PostFutureRevision,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Cria revisão imutável. Somente slots pendentes > T+30 a recebem.

    O RPC transacional usa o relógio do banco e conserva posts e mídias originais.
    A edição de novos arquivos ocorrerá na etapa de mídia, com vínculo durável.
    """
    profile_id = _require_profile_id(profile_id)
    post = _get_post(user_id, post_id, profile_id)
    _require_legacy_post_origin(post)
    if post.get("post_id") is not None or post.get("publish_immediately"):
        raise HTTPException(status_code=409, detail="Este post não admite edição futura")
    environment = current_environment()
    if not _has_revision_schedule_in_environment(user_id, post_id, profile_id, environment):
        raise HTTPException(status_code=409, detail="Post sem agenda elegível neste ambiente")

    original_ids = [product["id"] for product in _get_post_products(post_id)]
    if body.product_ids != original_ids:
        raise HTTPException(
            status_code=422,
            detail="Troca de produto não está disponível nesta revisão. O produto atual foi preservado.",
        )
    media_snapshot = _revision_media_snapshot(user_id, post_id, profile_id)
    _check_network_rules(
        post.get("network") or "threads",
        body.texts, media_snapshot, len(original_ids),
    )
    payload = {
        "texts": body.texts,
        "product_ids": original_ids,
        "medias": media_snapshot,
        "environment": environment,
    }
    try:
        result = supabase.rpc("create_future_post_revision", {
            "p_post_id": post_id,
            "p_user_id": str(user_id),
            "p_profile_id": str(profile_id),
            "p_snapshot": payload,
        }).execute()
    except Exception as exc:
        error = str(exc)
        if "POST_NOT_EDITABLE" in error or "NO_EDITABLE_FUTURE_SLOTS" in error:
            raise HTTPException(
                status_code=409,
                detail="Nenhuma ocorrência futura pode ser editada. O limite é 30 minutos antes de cada publicação.",
            ) from None
        logger.error("Falha de revisão futura: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Não foi possível salvar a revisão agora. Tente novamente."
        ) from None

    row = (result.data or [{}])[0] if isinstance(result.data, list) else (result.data or {})
    if not row.get("revision_id") or not row.get("cutover_at"):
        raise HTTPException(status_code=503, detail="A revisão não foi confirmada pelo banco")
    return {
        "post_id": post_id,
        "revision_id": row["revision_id"],
        "effective_after": row["cutover_at"],
        "msg": "Edição salva apenas para publicações futuras elegíveis.",
    }


@router.get("/{post_id}/future-revisions/latest")
def get_latest_future_revision(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Lê somente a revisão futura deste post, sem afetar GET /posts/{id}."""
    profile_id = _require_profile_id(profile_id)
    _get_post(user_id, post_id, profile_id)
    return {"revision": _latest_future_revision(user_id, post_id, profile_id)}


@router.put("/{post_id}")
async def update_post(
    post_id: int,
    body: PostUpdate,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Atualiza a head (id fixo — mantém agendamento/produtos válidos)
    e substitui as partes seguintes (apaga e recria — simplificação:
    não tenta casar partes antigas com as novas por id)."""
    profile_id = _require_profile_id(profile_id)
    post = _get_post(user_id, post_id, profile_id)  # ownership check
    _ensure_post_editable(user_id, post_id, profile_id, post)
    _validate_product_ids(user_id, body.product_ids)
    _check_network_rules(
        post.get("network") or "threads", body.texts,
        _get_post_medias(post_id), len(body.product_ids),
    )

    chain = _get_thread_chain(post_id, user_id)
    for row in reversed(chain[1:]):
        supabase.table("posts").delete().eq("id", row["id"]).execute()

    result = (
        scope_owner(
            supabase.table("posts").update({"text": body.texts[0]}).eq("id", post_id),
            user_id, profile_id,
        )
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Post não encontrado")

    parent_id = post_id
    for text in body.texts[1:]:
        row = (
            supabase.table("posts")
            .insert({
                "user_id": user_id, "text": text, "post_id": parent_id,
                "profile_id": profile_id,
            })
            .execute()
        )
        parent_id = row.data[0]["id"]

    _set_post_products(post_id, body.product_ids)
    return {
        **result.data[0],
        "texts": body.texts,
        "products": _get_post_products(post_id),
    }


@router.post("/{post_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_media(
    post_id: int,
    file: UploadFile,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Anexa uma mídia à HEAD do post (não a partes de thread — ver
    docstring do módulo). A mídia é sanitizada na memória e vai para o bucket
    privado `post-media` (`storage://`), nunca para o disco do servidor."""
    profile_id = _require_profile_id(profile_id)
    post = _get_post(user_id, post_id, profile_id)  # ownership check
    _ensure_post_editable(user_id, post_id, profile_id, post)

    content = await _read_media_content(file)
    media = await _sanitize_upload(file, content)
    content = media.content

    # regras da rede do post com o formato REAL (magic bytes), não o nome enviado
    _check_network_rules(
        post.get("network") or "threads", [post.get("text") or ""],
        [*_get_post_medias(post_id), {"file_name": media.safe_filename, "size": len(content)}],
        0,
    )

    # chave gerada no servidor (uuid + extensão real); NUNCA vem de `file.filename`
    storage_key = f"posts/{user_id}/{profile_id}/{post_id}/{uuid.uuid4().hex}{media.extension}"
    with storage_upload_reservation(len(content)):
        try:
            supabase.storage.from_(MEDIA_DRAFT_BUCKET).upload(
                storage_key, content, {"content-type": media.mime_type, "upsert": "false"}
            )
        except Exception:
            logger.warning("Falha ao guardar mídia do post", exc_info=True)
            raise HTTPException(status_code=502, detail="Não foi possível enviar a mídia agora. Tente novamente.")

    file_path = f"{STORAGE_SCHEME}{MEDIA_DRAFT_BUCKET}/{storage_key}"
    media_result = (
        supabase.table("medias")
        .insert({
            "user_id": user_id,
            "profile_id": profile_id,
            "file_name": media.safe_filename,
            "file_path": file_path,
            "size": len(content),
            "type": media.media_type,
        })
        .execute()
    )
    if not media_result.data:
        _remove_durable_media(file_path)
        raise HTTPException(status_code=500, detail="Falha ao salvar mídia")

    row = media_result.data[0]
    next_order = len(_get_post_medias(post_id))
    supabase.table("posts_medias").insert({
        "post_id": post_id,
        "media_id": row["id"],
        "display_order": next_order,
    }).execute()

    return row


@router.delete("/{post_id}/media/{media_id}")
async def delete_media(
    post_id: int,
    media_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    post = _get_post(user_id, post_id, profile_id)  # ownership check
    _ensure_post_editable(user_id, post_id, profile_id, post)

    media_result = (
        scope_owner(
            supabase.table("medias").select("file_path").eq("id", media_id),
            user_id, profile_id,
        )
        .maybe_single().execute()
    )
    if not media_result or not media_result.data:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")

    supabase.table("posts_medias").delete().eq("post_id", post_id).eq("media_id", media_id).execute()
    if _media_shared_elsewhere(media_id, post_id):
        return {"msg": "Mídia removida"}
    supabase.table("medias").delete().eq("id", media_id).execute()

    file_path = media_result.data.get("file_path")
    if file_path:
        _remove_media_file(file_path)

    return {"msg": "Mídia removida"}


@router.post("/{post_id}/publish")
async def publish_post_now(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Força a publicação imediata de um post já agendado."""
    post = _get_post(user_id, post_id, profile_id)
    _require_legacy_post_origin(post)  # ownership check
    _check_network_rules(
        post.get("network") or "threads",
        [row.get("text") or "" for row in _get_thread_chain(post_id, user_id)],
        _get_post_medias(post_id), len(_get_post_products(post_id)),
        check_required_media=True,
    )
    job = _get_scheduler_job(post_id)
    if not job:
        raise HTTPException(status_code=409, detail="Post não tem agendamento — nada pra publicar")

    network = post.get("network") or "threads"
    if job.get("trigger") == "date":
        latest = _latest_publish_job(user_id, post_id, profile_id)
        if latest and latest.get("status") in ("running", "unknown", "succeeded"):
            raise HTTPException(
                status_code=409,
                detail="Publicação já iniciada ou sem confirmação. Verifique o resultado antes de reenviar.",
            )
    reserve_post_plan_quota(
        user_id, profile_id, post_id, immediate=True,
        reuse_existing=bool(post.get("publish_immediately") and job.get("trigger") == "date"),
    )
    log_action(
        "post_publish_requested",
        f"network={network} post_id={post_id} job_id={job['id']}",
        user_id=user_id,
        profile_id=profile_id,
    )

    try:
        await run_scheduler_job(job["id"])
    except InternalApiError as err:
        log_action(
            "post_publish_dispatch_failed",
            f"network={network} post_id={post_id} job_id={job['id']} stage=dispatch error={err}",
            user_id=user_id,
            profile_id=profile_id,
        )
        raise HTTPException(status_code=502, detail="Não foi possível publicar agora. Tente novamente.")

    # 200 aqui = job disparado, não publicado: o resultado real chega em
    # segundos em `last_result` (GET /posts) e em Atividade.
    return {"msg": "Publicação iniciada. O resultado aparece no post em instantes."}


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    post = _get_post(user_id, post_id, profile_id)  # ownership check
    _require_legacy_post_origin(post)

    jobs = supabase.table("schedulers").select("id").eq("post_id", post_id).execute().data or []
    for job in jobs:
        try:
            await remove_scheduler_job(user_id, job["id"])
        except InternalApiError:
            raise HTTPException(
                status_code=502,
                detail="Não foi possível remover o agendamento agora. Post não foi removido.",
            )

    _delete_thread_cascade(post_id, user_id)
    return {"msg": "Post removido"}
