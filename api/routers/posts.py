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
from pathlib import Path
from typing import Literal

import fleep
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, model_validator, field_validator

from .auth import _check_login_rate_limit, get_current_user_id
from .profiles import get_current_profile_id
from ..profiles import scope_account, scope_owner
from ..audit_log import log_action
from ..database import supabase
from ..utils.log_sanitizer import sanitize_log_data
from ..network_limits import validate_post, errors_detail
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

# MIME real detectado por magic bytes (fleep) -> extensão gravada em disco.
# O nome do arquivo é gerado no servidor (uuid + esta extensão), NUNCA vem de
# `file.filename` (path traversal: "../../x.png", absoluto, "..\\x.png").
# Mesmo padrão do avatar em api/routers/profiles.py.
ALLOWED_MEDIA_MIMES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
}


def _remove_media_file(file_path: str) -> None:
    """Apaga um arquivo de mídia só se ele estiver dentro de MEDIA_ROOT —
    `file_path` vem do banco e pode ter sido gravado por versões antigas
    sem sanitização (ex.: "web/media/1/../../../x")."""
    resolved = Path(file_path).resolve()
    if not resolved.is_relative_to(MEDIA_ROOT.resolve()):
        logger.warning("Remoção de mídia fora de MEDIA_ROOT recusada: %s", file_path)
        return
    try:
        resolved.unlink(missing_ok=True)  # já sumiu: não bloqueia a remoção do post
    except OSError:
        logger.warning("Falha ao remover arquivo de mídia %s", file_path, exc_info=True)


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


def _media_shared_elsewhere(media_id: int, post_id: int) -> bool:
    """A mesma mídia pode estar ligada a vários posts (grupo multi-rede):
    arquivo e linha em `medias` só somem quando ninguém mais usa."""
    rows = (
        supabase.table("posts_medias").select("post_id").eq("media_id", media_id).execute()
    )
    return any(r.get("post_id") != post_id for r in (rows.data or []))


def _get_scheduler_job(post_id: int) -> dict | None:
    result = (
        supabase.table("schedulers").select("id")
        .eq("post_id", post_id).maybe_single().execute()
    )
    return result.data if result else None


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
            "scheduled": job is not None,
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
        await create_scheduler_job(
            user_id=user_id,
            post_id=head["id"],
            func=NETWORK_FUNC_MAP[body.network],
            trigger=body.schedule.trigger,
            time=body.schedule.time,
            day_of_week=body.schedule.day_of_week,
            start_date=body.schedule.start_date,
            run_date=body.schedule.run_date,
            profile_id=profile_id,
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
        "medias": medias,
        "scheduled": True,
    }


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
        "scheduled": job is not None,
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
    docstring do módulo). Grava em disco no mesmo caminho relativo que
    o Flask usa (`web/media/<post_id>/`)."""
    profile_id = _require_profile_id(profile_id)
    post = _get_post(user_id, post_id, profile_id)  # ownership check

    content = await file.read()
    if len(content) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o tamanho máximo (50MB)")

    detected = fleep.get(content[:128])
    mime = next((m for m in detected.mime if m in ALLOWED_MEDIA_MIMES), None)
    if not mime:
        raise HTTPException(
            status_code=400,
            detail="Conteúdo do arquivo não corresponde a uma mídia permitida.",
        )

    # regras da rede do post com o formato REAL (magic bytes), não o nome enviado
    shown_name = f"{Path(file.filename or 'arquivo').stem}{ALLOWED_MEDIA_MIMES[mime]}"
    _check_network_rules(
        post.get("network") or "threads", [post.get("text") or ""],
        [*_get_post_medias(post_id), {"file_name": shown_name, "size": len(content)}],
        0,
    )

    post_dir = MEDIA_ROOT / str(post_id)
    post_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ALLOWED_MEDIA_MIMES[mime]}"
    file_path = post_dir / filename
    if not file_path.resolve().is_relative_to(post_dir.resolve()):  # defesa extra
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")
    file_path.write_bytes(content)

    media_type = "VIDEO" if mime.startswith("video/") else "IMAGE"
    media_result = (
        supabase.table("medias")
        .insert({
            "user_id": user_id,
            "profile_id": profile_id,
            "file_name": filename,
            "file_path": str(file_path),
            "size": len(content),
            "type": media_type,
        })
        .execute()
    )
    if not media_result.data:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Falha ao salvar mídia")

    media = media_result.data[0]
    next_order = len(_get_post_medias(post_id))
    supabase.table("posts_medias").insert({
        "post_id": post_id,
        "media_id": media["id"],
        "display_order": next_order,
    }).execute()

    return media


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

    try:
        await run_scheduler_job(job["id"])
    except InternalApiError:
        raise HTTPException(status_code=502, detail="Não foi possível publicar agora. Tente novamente.")

    log_action("post_published", f"post_id={post_id}", user_id=user_id, profile_id=profile_id)
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
