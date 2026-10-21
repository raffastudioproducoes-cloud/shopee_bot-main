"""
Posts Router — API Python (FastAPI)

CRUD de posts (thread multi-parte) + copywriter IA + agendamento/
publicação. Agendamento/publicação passam pelo bridge interno
(`api/internal_client.py` -> `web/routes/internal.py`) porque o
APScheduler só roda de verdade no processo Flask — ver docstring de
internal_client.py e Fase 8 em docs/ROADMAP_MIGRACAO.md.

Upload de mídia (imagem/vídeo) grava em `web/media/<post_id>/`, o MESMO
caminho relativo que o Flask usa — funciona de verdade quando os dois
processos rodam a partir da mesma raiz de repositório (dev local hoje;
em produção só funciona se um dia forem deployados compartilhando o
mesmo filesystem, o que ainda não é o caso — só o Flask está no
Render). Cifrado pro Cloudinary só acontece na publicação
(`scheduler/bot_post.py`, roda no Flask). Simplificação: mídia só na
head da thread, não em cada parte (mesma limitação de UI do form novo).

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
import uuid
from datetime import datetime, timedelta, timezone
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, model_validator, field_validator

from .auth import _check_login_rate_limit, get_current_user_id
from .profiles import get_current_profile_id
from ..profiles import scope_account, scope_owner
from ..audit_log import log_action
from ..database import supabase
from ..utils.log_sanitizer import sanitize_log_data
from ..network_limits import validate_post, errors_detail, is_network_disabled
from ..media_composition import plan_network_composition
from ..media_sanitizer import MediaSanitizerError, sanitize_media_upload
from .. import x_oauth
from ..text_variants import generate_variants
from ..internal_client import (
    create_scheduler_job,
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
    """Valida e reencoda o upload na memória; falha vira HTTP sem eco do conteúdo."""
    try:
        return await run_in_threadpool(
            sanitize_media_upload,
            content,
            filename=file.filename,
            content_type=file.content_type,
            max_bytes=MAX_MEDIA_BYTES,
        )
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

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, v):
        if not v or not any(t.strip() for t in v):
            raise ValueError("texts precisa ter ao menos um item com texto")
        return v


class PostComposition(BaseModel):
    network: NetworkLiteral
    texts: list[str]

    @field_validator("texts")
    @classmethod
    def _texts_not_empty(cls, value):
        if not value or not any(text.strip() for text in value):
            raise ValueError("texts precisa ter ao menos um item com texto")
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
            raise ValueError("publish_immediately requer trigger 'date'")
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
        return v


class GenerateCopyBody(BaseModel):
    product_id: int
    persona: str = "casual"
    # Provedor de IA (gemini/openai/anthropic). Omitido: o único salvo ou o
    # salvo mais recentemente pelo usuário/perfil (ver resolve_ai_key).
    provider: str | None = None
    # Redes marcadas: um texto por faixa de limite (api/text_variants.py).
    networks: list[NetworkLiteral] = []


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


def _block_reason(exc: Exception) -> str:
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
        _delete_thread_cascade(head_id)
    except Exception:
        logger.error("Falha ao desfazer post %s após erro no lote", head_id, exc_info=True)


def _media_shared_elsewhere(media_id: int, post_id: int) -> bool:
    """A mesma mídia pode estar ligada a vários posts (grupo multi-rede):
    arquivo e linha em `medias` só somem quando ninguém mais usa."""
    rows = (
        supabase.table("posts_medias").select("post_id").eq("media_id", media_id).execute()
    )
    return any(r.get("post_id") != post_id for r in (rows.data or []))


def _get_scheduler_job(post_id: int) -> dict | None:
    result = (
        supabase.table("schedulers").select("id,trigger")
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
    except Exception:
        for job_id in created:
            try:
                await remove_scheduler_job(user_id, job_id)
            except InternalApiError:
                logger.error("Falha ao desfazer job recorrente %s", job_id, exc_info=True)
        raise


# activity_types (migração 005): 1=bot_post_success, 2=bot_post_failure —
# gravados pelos bots do scheduler (Flask) e pelo listener de erro/missed.
_PUBLISH_ACTIVITY_STATUS = {1: "published", 2: "failed"}


def _get_last_publish_result(user_id: int, post_id: int) -> dict | None:
    """Último resultado REAL da publicação do post (a execução acontece no
    scheduler, depois do 200 de /publish). Best-effort: falha aqui não
    derruba a listagem."""
    try:
        result = (
            supabase.table("activities").select("activity_id, metadata, created_at")
            .eq("user_id", user_id)
            .in_("activity_id", list(_PUBLISH_ACTIVITY_STATUS))
            .eq("metadata->>post_id", str(post_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning("Falha ao ler resultado de publicação do post %s", post_id, exc_info=True)
        return None
    rows = result.data if isinstance(getattr(result, "data", None), list) else []
    if not rows:
        return None
    row = rows[0]
    error = (row.get("metadata") or {}).get("error")
    return {
        "status": _PUBLISH_ACTIVITY_STATUS.get(row.get("activity_id")),
        "at": row.get("created_at"),
        "error": sanitize_log_data(str(error))[:200] if error else None,
    }


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
    parent_id = None
    head = None
    for text in texts:
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


def _delete_thread_cascade(head_id: int) -> None:
    """Apaga a thread inteira (head + partes) + associações de produto
    e mídia (arquivo em disco + linhas). Usado no DELETE e pra desfazer
    a criação se o agendamento falhar."""
    chain = _get_thread_chain(head_id)

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
    """Gera texto de post via IA para um produto, por persona, com a chave de
    IA do PRÓPRIO usuário/perfil (Credenciais). Sem chave global: sem chave
    cadastrada -> 400 pedindo pra cadastrar.

    Com `networks`, devolve o conjunto mínimo de textos (`variants`, um por
    faixa de limite) numa só chamada; `text` = variante principal (a mais
    longa), compatível com o front antigo."""
    from apis import llm
    from .credentials import resolve_ai_key

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

    provider, api_key, model = resolve_ai_key(user_id, profile_id, body.provider)

    def complete(prompt: str, max_tokens: int) -> str:
        return llm.complete(provider, api_key, model, prompt, max_tokens)

    try:
        variants = await run_in_threadpool(
            generate_variants, product_result.data, body.persona, body.networks, complete,
        )
    except llm.LLMError as e:
        # mensagem do LLMError já é segura (sem chave nem corpo do provedor)
        logger.warning("Falha ao gerar texto do produto %s (%s): %s", body.product_id, provider, e.kind)
        raise HTTPException(status_code=400, detail=str(e))

    return {"text": variants[0]["text"], "variants": variants}


@router.get("")
async def list_posts(
    user_id: int = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    cursor: str | None = Query(None, description="Cursor de paginação (created_at)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Lista posts únicos (post_id IS NULL — sem thread) com paginação por cursor."""
    query = (
        scope_owner(supabase.table("posts").select("*"), user_id, profile_id)
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
            "medias": _get_post_medias(item["id"]),
            "scheduled": _is_scheduled(job, item),
            "schedule_trigger": job.get("trigger") if job else None,
            "parts_count": len(chain),
            "last_result": _get_last_publish_result(user_id, item["id"]),
        })

    next_cursor = None
    if result.data and len(result.data) == limit:
        next_cursor = result.data[-1]["created_at"]

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
        await _create_schedule_jobs(user_id, head["id"], NETWORK_FUNC_MAP[body.network], body.schedule, profile_id)
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
                "texts": composition.texts,
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
            "texts": composition.texts,
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
            _set_post_products(head["id"], body.product_ids)
            medias = _attach_medias(
                head["id"], plan["media_draft_ids"], drafts_by_id, materialized, fresh,
                user_id, profile_id,
            )
            # job por último: sem mídia vinculada ele nunca existe
            await _create_schedule_jobs(user_id, head["id"], NETWORK_FUNC_MAP[plan["network"]], body.schedule, profile_id)
        except Exception as exc:
            if not isinstance(exc, (InternalApiError, _DraftUnavailable)):
                logger.warning("Falha ao montar post da rede %s", plan["network"], exc_info=True)
            _rollback_plan(head["id"], fresh, materialized, user_id, profile_id)
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
        supabase.storage.from_(MEDIA_DRAFT_BUCKET).upload(
            storage_key, content, {"content-type": mime, "upsert": "false"}
        )
    except Exception:
        supabase.table("temporary_media_uploads").delete().eq("id", upload_id).eq("status", "uploading").execute()
        logger.warning("Falha ao guardar rascunho de mídia", exc_info=True)
        raise HTTPException(status_code=502, detail="Não foi possível enviar a mídia agora. Tente novamente.")

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
    job = _get_scheduler_job(post_id)
    chain = _get_thread_chain(post_id)
    return {
        **post,
        "texts": [row["text"] for row in chain],
        "products": _get_post_products(post_id),
        "medias": _get_post_medias(post_id),
        "scheduled": _is_scheduled(job, post),
        "schedule_trigger": job.get("trigger") if job else None,
        "last_result": _get_last_publish_result(user_id, post_id),
    }


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
    _validate_product_ids(user_id, body.product_ids)
    _check_network_rules(
        post.get("network") or "threads", body.texts,
        _get_post_medias(post_id), len(body.product_ids),
    )

    chain = _get_thread_chain(post_id)
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
    _get_post(user_id, post_id, profile_id)  # ownership check

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
    post = _get_post(user_id, post_id, profile_id)  # ownership check
    _check_network_rules(
        post.get("network") or "threads",
        [row.get("text") or "" for row in _get_thread_chain(post_id)],
        _get_post_medias(post_id), len(_get_post_products(post_id)),
        check_required_media=True,
    )
    job = _get_scheduler_job(post_id)
    if not job:
        raise HTTPException(status_code=409, detail="Post não tem agendamento — nada pra publicar")

    network = post.get("network") or "threads"
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
    _get_post(user_id, post_id, profile_id)  # ownership check

    jobs = supabase.table("schedulers").select("id").eq("post_id", post_id).execute().data or []
    for job in jobs:
        try:
            await remove_scheduler_job(user_id, job["id"])
        except InternalApiError:
            raise HTTPException(
                status_code=502,
                detail="Não foi possível remover o agendamento agora. Post não foi removido.",
            )

    _delete_thread_cascade(post_id)
    return {"msg": "Post removido"}
