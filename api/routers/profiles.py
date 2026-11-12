"""
Profiles Router — API Python (FastAPI)

CRUD de perfis (multi-profile) e troca de perfil ativo (`/profiles/{id}/activate`).
"""

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from ..database import supabase
from ..effective_plan import effective_plan
from ..storage_capacity import storage_upload_reservation
from ..media_sanitizer import JPEG, PNG, WEBP, MediaSanitizerError, detect_media_type, sanitize_media_upload
from ..profiles import is_principal
from .auth import (
    _check_login_rate_limit,
    _create_token,
    _decode_token,
    _get_user_from_supabase,
    _password_version,
    _revoke_session,
    _retry_readonly_auth_query,
    get_current_user_id,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])
logger = logging.getLogger(__name__)

# Avatar: só imagens (JPEG/PNG/WEBP), validadas pelo conteúdo real e reencodadas
# sem metadados por api/media_sanitizer.py. A extensão no bucket vem do tipo real,
# nunca de file.filename (path traversal; perfil tem 1 avatar por vez).
ALLOWED_AVATAR_TYPES = (JPEG, PNG, WEBP)
AVATAR_BUCKET = "avatars"
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5MB, avatar não precisa do teto de 50MB de posts.py


def _archive_enabled() -> bool:
    """Nunca efetuar DELETE físico se a migração/rollout ainda não foi ativada."""
    return os.getenv("PROFILE_ARCHIVAL_ENABLED", "false").lower() == "true"


def _active_profile_query(query):
    # Somente após o rollout aditivo; antigas versões não conhecem archived_at.
    return query.is_("archived_at", "null") if _archive_enabled() else query


class ProfileCreate(BaseModel):
    nome: str
    # Contatos da conta vivem em account_billing_identity; campos legados
    # continuam aceitos para não quebrar clientes antigos em produção.
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None


class ProfileUpdate(BaseModel):
    nome: str
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None


def _resolve_profile_id(profile_id: str | None, user_id: str) -> str | None:
    """Confirma que o perfil do token pertence ao usuário (perfil excluído
    ou de outra conta não vale). Se não pertencer, cai no perfil principal
    do usuário; sem principal, None (sem filtro por perfil)."""
    owned = profile_id and _retry_readonly_auth_query(
        lambda: _active_profile_query(
            supabase.table("profiles")
            .select("id")
            .eq("id", profile_id)
            .eq("user_id", user_id)
        ).maybe_single().execute()
    )
    if owned and owned.data:
        return profile_id
    principal = _retry_readonly_auth_query(
        lambda: _active_profile_query(
            supabase.table("profiles")
            .select("id")
            .eq("user_id", user_id)
            .eq("kind", "principal")
        ).maybe_single().execute()
    )
    return principal.data["id"] if principal and principal.data else None


def get_current_profile_id(
    request: Request, user_id: str = Depends(get_current_user_id)
) -> str | None:
    """Claim opcional -- token emitido antes desta feature não tem profile_id;
    nesse caso (ou claim inválido) cai no perfil principal do usuário, para
    nunca operar sem escopo de perfil quando o usuário tem perfis."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    return _resolve_profile_id(payload.get("profile_id"), user_id)


def _get_own_profile_or_404(profile_id: str, user_id: str) -> dict:
    """Busca um perfil do usuário autenticado, dando 404 se não existir ou
    pertencer a outra conta -- usado por update/delete/activate."""
    existing = _active_profile_query(
        supabase.table("profiles")
        .select("*")
        .eq("id", profile_id)
        .eq("user_id", user_id)
    ).maybe_single().execute()
    if not existing or not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return existing.data


@router.get("")
async def list_profiles(user_id: str = Depends(get_current_user_id)):
    # Consulta idempotente: reconexões HTTP/2 do PostgREST não devem virar 500.
    # Executar o cliente síncrono fora do event loop; nunca repetir escritas.
    result = await run_in_threadpool(
        _retry_readonly_auth_query,
        lambda: _active_profile_query(
            # A lista de cards não precisa reenviar dados legados de contato.
            supabase.table("profiles").select("id,user_id,kind,plan_tier,nome,avatar_url").eq("user_id", user_id)
        ).execute(),
    )
    return result.data



@router.get("/quota")
async def get_profile_quota(user_id: str = Depends(get_current_user_id)):
    """Consulta apenas o entitlement canônico da conta, nunca o tier do browser."""
    try:
        account = (supabase.table("users").select("access,plan_tier")
                   .eq("id", user_id).maybe_single().execute())
        if not account or not account.data:
            raise HTTPException(status_code=404, detail="Conta não encontrada.")
        tier = effective_plan(account.data["access"], account.data["plan_tier"])
        is_admin = account.data["access"] == "ADMIN"
        limit = None
        if not is_admin:
            policy = (supabase.table("plan_limits")
                      .select("max_profiles_per_account").eq("tier", tier)
                      .maybe_single().execute())
            if not policy or not policy.data:
                raise HTTPException(status_code=503, detail="Política de planos indisponível.")
            limit = policy.data["max_profiles_per_account"]
        rows = _active_profile_query(
            supabase.table("profiles").select("id").eq("user_id", user_id)
        ).execute()
        return {
            "tier": tier, "used": len(rows.data or []),
            "limit": limit, "unlimited": is_admin,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Falha ao consultar a cota de perfis")
        raise HTTPException(status_code=503, detail="Não foi possível consultar o limite de perfis.")




# Independent, revocable regional preference. Never inferred from profile addresses or IPs.
ALLOWED_REGIONS = frozenset(("BR-RJ","BR-SP","BR-MG","BR-BA","BR-OTHER","PT","US","GB","DE","JP","AU","OTHER"))


class RegionPreference(BaseModel):
    region: str
    consent: bool = False


class LocationDecision(BaseModel):
    choice: str
    latitude: float | None = None
    longitude: float | None = None
    accuracy_m: int | None = None


@router.get("/usage")
async def get_plan_usage(
    user_id: str = Depends(get_current_user_id),
    profile_id: str = Depends(get_current_profile_id),
):
    """Somente leitura, autenticada e isolada por conta/perfil."""
    if not profile_id:
        raise HTTPException(status_code=400, detail="Selecione um perfil válido.")
    from ..account_usage import account_usage_response
    return await run_in_threadpool(account_usage_response, user_id, profile_id)


@router.get("/location-sharing")
async def get_location_sharing(user_id: str = Depends(get_current_user_id)):
    result = await run_in_threadpool(
        _retry_readonly_auth_query,
        lambda: (
            supabase.table("account_location_sharing")
            .select("choice,latitude,longitude,collected_at")
            .eq("user_id", user_id).limit(1).execute()
        ),
    )
    row = (result.data or [None])[0]
    return row or {"choice": "pending", "latitude": None, "longitude": None, "collected_at": None}


@router.put("/location-sharing")
async def put_location_sharing(body: LocationDecision, user_id: str = Depends(get_current_user_id)):
    """Uma única decisão/coleta por conta; revogação mantém um registro sem coordenadas.

    A chave primária do banco protege contra duas solicitações simultâneas.
    Sem recolhimento de GPS após uma primeira decisão, mesmo após revogação.
    """
    from datetime import datetime, timezone
    from math import isfinite

    if body.choice not in ("accepted", "declined", "revoked"):
        raise HTTPException(status_code=422, detail="Escolha inválida")

    result = (
        supabase.table("account_location_sharing")
        .select("choice").eq("user_id", user_id).limit(1).execute()
    )
    current = (result.data or [None])[0]
    now = datetime.now(timezone.utc).isoformat()

    if body.choice == "revoked":
        if current and current["choice"] == "revoked":
            return {"choice": "revoked"}
        if current:
            supabase.table("account_location_sharing").update({
                "choice": "revoked", "latitude": None, "longitude": None,
                "accuracy_m": None, "collected_at": None, "decided_at": now,
            }).eq("user_id", user_id).execute()
        else:
            supabase.table("account_location_sharing").insert({
                "user_id": user_id, "choice": "revoked",
                "consent_version": "2026-10-31", "decided_at": now,
            }).execute()
        return {"choice": "revoked"}

    if current:
        raise HTTPException(status_code=409, detail="A decisão de localização já foi registrada.")

    row = {
        "user_id": user_id, "choice": body.choice,
        "consent_version": "2026-10-31", "decided_at": now,
        "latitude": None, "longitude": None,
        "accuracy_m": None, "collected_at": None,
    }
    if body.choice == "accepted":
        if (body.latitude is None or body.longitude is None
                or not isfinite(body.latitude) or not isfinite(body.longitude)
                or not (-90 <= body.latitude <= 90)
                or not (-180 <= body.longitude <= 180)):
            raise HTTPException(status_code=422, detail="Coordenadas inválidas")
        if body.accuracy_m is not None and not (0 <= body.accuracy_m <= 1000000):
            raise HTTPException(status_code=422, detail="Precisão inválida")
        row.update({
            "latitude": round(body.latitude, 2),
            "longitude": round(body.longitude, 2),
            "accuracy_m": body.accuracy_m, "collected_at": now,
        })
    elif body.latitude is not None or body.longitude is not None or body.accuracy_m is not None:
        raise HTTPException(status_code=422, detail="Recusa não pode conter localização.")

    try:
        supabase.table("account_location_sharing").insert(row).execute()
    except Exception as exc:
        if "23505" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(status_code=409, detail="A decisão de localização já foi registrada.") from exc
        logger.exception("Falha ao registrar decisão de localização")
        raise HTTPException(status_code=503, detail="Não foi possível registrar a decisão.") from exc
    return {"choice": body.choice}


@router.get("/gps-preference")
async def get_gps_preference(user_id: str = Depends(get_current_user_id)):
    result = await run_in_threadpool(
        _retry_readonly_auth_query,
        lambda: supabase.table("users").select("gps_consented_at").eq("id", user_id).limit(1).execute(),
    )
    account = (result.data or [None])[0]
    return {"enabled": bool(account and account.get("gps_consented_at"))}


class GpsConsent(BaseModel):
    enabled: bool


@router.put("/gps-preference")
async def put_gps_preference(body: GpsConsent, user_id: str = Depends(get_current_user_id)):
    from datetime import datetime, timezone
    # Preference is not OS/browser geolocation permission and does not collect coordinates.
    change = {
        "gps_consented_at": datetime.now(timezone.utc).isoformat() if body.enabled else None,
        "gps_consent_version": "2026-10-30" if body.enabled else None,
    }
    supabase.table("users").update(change).eq("id", user_id).execute()
    if not body.enabled:
        supabase.table("account_region_preferences").delete().eq("user_id", user_id).execute()
    return {"enabled": body.enabled}


@router.get("/region-preference")
async def get_region_preference(user_id: str = Depends(get_current_user_id)):
    # Uma preferência ainda não cadastrada deve retornar resposta vazia,
    # não depender de .maybe_single() (pode lançar 406 com zero linhas).
    result = await run_in_threadpool(
        _retry_readonly_auth_query,
        lambda: (
            supabase.table("account_region_preferences")
            .select("region")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ),
    )
    preference = (result.data or [None])[0]
    return {"region": preference["region"] if preference else None, "consented": bool(preference)}


@router.put("/region-preference")
async def put_region_preference(body: RegionPreference, user_id: str = Depends(get_current_user_id)):
    if not body.consent or body.region not in ALLOWED_REGIONS:
        raise HTTPException(status_code=422, detail="Selecione uma região válida e confirme o consentimento.")
    supabase.table("account_region_preferences").upsert({"user_id": user_id, "region": body.region}, on_conflict="user_id").execute()
    return {"region": body.region, "consented": True}


@router.delete("/region-preference")
async def delete_region_preference(user_id: str = Depends(get_current_user_id)):
    supabase.table("account_region_preferences").delete().eq("user_id", user_id).execute()
    return {"region": None, "consented": False}

ALLOWED_ACQUISITION_SOURCES = frozenset(("search", "social", "referral", "direct", "other"))


class AcquisitionPreference(BaseModel):
    source: str
    consent: bool = False


@router.get("/acquisition-source")
async def get_acquisition_source(user_id: str = Depends(get_current_user_id)):
    # Primeiro acesso: zero registros é normal e não pode bloquear o formulário.
    result = await run_in_threadpool(
        _retry_readonly_auth_query,
        lambda: (
            supabase.table("account_acquisition_sources")
            .select("source")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ),
    )
    preference = (result.data or [None])[0]
    return {"source": preference["source"] if preference else None, "declared": bool(preference)}


@router.put("/acquisition-source")
async def put_acquisition_source(body: AcquisitionPreference, user_id: str = Depends(get_current_user_id)):
    if not body.consent or body.source not in ALLOWED_ACQUISITION_SOURCES:
        raise HTTPException(status_code=422, detail="Informe uma origem válida e confirme que deseja compartilhá-la.")
    supabase.table("account_acquisition_sources").upsert({"user_id": user_id, "source": body.source}, on_conflict="user_id").execute()
    return {"source": body.source, "declared": True}


@router.delete("/acquisition-source")
async def delete_acquisition_source(user_id: str = Depends(get_current_user_id)):
    supabase.table("account_acquisition_sources").delete().eq("user_id", user_id).execute()
    return {"source": None, "declared": False}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreate, user_id: str = Depends(get_current_user_id)):
    _check_login_rate_limit(f"profile-create:{user_id}")
    limit_detail = "Limite de perfis do seu plano atingido."
    try:
        # A RPC serializa as tentativas por conta e aplica Free=1, Pro=3,
        # Premium=5 e isenção comercial ADMIN usando somente o papel no DB.
        # O trigger legado mantém o máximo antigo para a main (DB compartilhado).
        result = supabase.rpc("insert_profile_with_plan_quota", {
            "p_user_id": user_id,
            "p_nome": body.nome.strip(),
            "p_email": body.email.strip() if body.email else None,
            "p_telefone": body.telefone.strip() if body.telefone else None,
            "p_endereco": body.endereco.strip() if body.endereco else None,
        }).execute()
    except Exception as exc:
        # A RPC e a barreira atômica do banco retornam códigos sem dados privados.
        if "profile_limit_exceeded" in str(exc):
            raise HTTPException(status_code=403, detail=limit_detail) from None
        if "plan_policy_unavailable" in str(exc):
            raise HTTPException(status_code=503, detail="Política de planos indisponível.") from None
        logger.exception("Falha ao criar perfil")
        raise HTTPException(status_code=500, detail="Erro interno ao criar perfil.")
    if not result.data:
        raise HTTPException(status_code=500, detail="Erro interno ao criar perfil.")
    return result.data[0]


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str, body: ProfileUpdate, user_id: str = Depends(get_current_user_id)
):
    _get_own_profile_or_404(profile_id, user_id)
    updates = {"nome": body.nome.strip()}
    for field in ("email", "telefone", "endereco"):
        # Edição só do nome NÃO apaga dados legados do perfil.
        if field in body.model_fields_set:
            value = getattr(body, field)
            updates[field] = value.strip() if value else None
    result = (
        supabase.table("profiles")
        .update(updates)
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0]


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, user_id: str = Depends(get_current_user_id)):
    existing = _get_own_profile_or_404(profile_id, user_id)
    if is_principal(existing):
        raise HTTPException(status_code=400, detail="O perfil principal não pode ser excluído")
    if not _archive_enabled():
        raise HTTPException(
            status_code=503,
            detail="Exclusão segura em preparação. Nenhum perfil foi removido.",
        )
    try:
        result = await run_in_threadpool(
            lambda: supabase.rpc("archive_profile_with_history", {
                "p_user_id": user_id, "p_profile_id": profile_id,
            }).execute()
        )
    except Exception:
        logger.exception("Falha na operação transacional de arquivamento de perfil")
        raise HTTPException(
            status_code=503, detail="Não foi possível arquivar o perfil com segurança."
        ) from None
    if not result.data:
        raise HTTPException(status_code=503, detail="Arquivamento não confirmado pelo banco.")
    return {"status": "archived"}


@router.post("/{profile_id}/activate")
async def activate_profile(
    profile_id: str,
    response: Response,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    _get_own_profile_or_404(profile_id, user_id)

    token = request.cookies.get("access_token")
    payload = _decode_token(token) if token else None
    username = payload.get("sub") if payload else None
    # pwv sempre do hash ATUAL (não copiado do token antigo): token legado
    # sem pwv passa a expirar após troca de senha.
    user = _get_user_from_supabase(username) if username else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuário inexistente")
    new_token = _create_token({
        "sub": username,
        "id": user_id,
        "profile_id": profile_id,
        "pwv": _password_version(user.get("password")),
    })
    _revoke_session(token, user_id)

    # Flags idênticos ao endpoint de login (api/routers/auth.py::login) --
    # confirmado por leitura direta do handler, não reinventados aqui.
    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400,
    )
    return {"status": "activated", "profile_id": profile_id}


@router.post("/{profile_id}/avatar")
async def upload_avatar(
    profile_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    _get_own_profile_or_404(profile_id, user_id)

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o tamanho máximo (5MB)")

    try:
        detected = detect_media_type(content)
        if detected not in ALLOWED_AVATAR_TYPES:
            raise MediaSanitizerError("formato não permitido para avatar")
        # nome/tipo declarados pelo cliente nunca valeram pro avatar: só o conteúdo real
        media = await run_in_threadpool(
            sanitize_media_upload,
            content,
            filename=f"avatar{detected.extension}",
            content_type=detected.mime_type,
            max_bytes=MAX_AVATAR_BYTES,
        )
    except MediaSanitizerError:
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem válida.") from None

    path = f"{profile_id}/avatar{media.extension}"
    with storage_upload_reservation(len(media.content)):
        supabase.storage.from_(AVATAR_BUCKET).upload(
            path, media.content, {"content-type": media.mime_type, "upsert": "true"}
        )
    public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)

    supabase.table("profiles").update({"avatar_url": public_url}).eq(
        "id", profile_id
    ).eq("user_id", user_id).execute()
    return {"avatar_url": public_url}
