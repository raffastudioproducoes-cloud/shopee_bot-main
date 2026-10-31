"""
Profiles Router — API Python (FastAPI)

CRUD de perfis (multi-profile) e troca de perfil ativo (`/profiles/{id}/activate`).
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from ..database import supabase
from ..media_sanitizer import JPEG, PNG, WEBP, MediaSanitizerError, detect_media_type, sanitize_media_upload
from ..profiles import PROFILE_LIMIT, can_create_profile, is_principal
from .auth import (
    _check_login_rate_limit,
    _create_token,
    _decode_token,
    _get_user_from_supabase,
    _password_version,
    _revoke_session,
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


class ProfileCreate(BaseModel):
    nome: str
    email: str
    telefone: str | None = None
    endereco: str | None = None


class ProfileUpdate(BaseModel):
    nome: str
    email: str
    telefone: str | None = None
    endereco: str | None = None


def _resolve_profile_id(profile_id: str | None, user_id: str) -> str | None:
    """Confirma que o perfil do token pertence ao usuário (perfil excluído
    ou de outra conta não vale). Se não pertencer, cai no perfil principal
    do usuário; sem principal, None (sem filtro por perfil)."""
    owned = profile_id and (
        supabase.table("profiles")
        .select("id")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if owned and owned.data:
        return profile_id
    principal = (
        supabase.table("profiles")
        .select("id")
        .eq("user_id", user_id)
        .eq("kind", "principal")
        .maybe_single()
        .execute()
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
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing or not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return existing.data


@router.get("")
async def list_profiles(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return result.data



# Independent, revocable regional preference. Never inferred from profile addresses or IPs.
ALLOWED_REGIONS = frozenset(("BR-RJ","BR-SP","BR-MG","BR-BA","BR-OTHER","PT","US","GB","DE","JP","AU","OTHER"))


class RegionPreference(BaseModel):
    region: str
    consent: bool = False


@router.get("/gps-preference")
async def get_gps_preference(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("users").select("gps_consented_at").eq("id", user_id).limit(1).execute()
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
    result = (
        supabase.table("account_region_preferences")
        .select("region")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
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
    result = (
        supabase.table("account_acquisition_sources")
        .select("source")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
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
    limit_detail = f"Limite de {PROFILE_LIMIT} perfis por conta atingido."
    existing = supabase.table("profiles").select("id").eq("user_id", user_id).execute()
    if not can_create_profile(len(existing.data or [])):
        raise HTTPException(status_code=400, detail=limit_detail)
    try:
        result = (
            supabase.table("profiles")
            .insert({
                "user_id": user_id,
                "kind": "secundario",
                "nome": body.nome.strip(),
                "email": body.email.strip(),
                "telefone": body.telefone.strip() if body.telefone else None,
                "endereco": body.endereco.strip() if body.endereco else None,
            })
            .execute()
        )
    except Exception as exc:
        # O check acima tem race (count-then-insert); o trigger do banco
        # (migração 037) é a barreira atômica e levanta profile_limit_exceeded.
        if "profile_limit_exceeded" in str(exc):
            raise HTTPException(status_code=400, detail=limit_detail)
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
    result = (
        supabase.table("profiles")
        .update({
            "nome": body.nome.strip(),
            "email": body.email.strip(),
            "telefone": body.telefone.strip() if body.telefone else None,
            "endereco": body.endereco.strip() if body.endereco else None,
        })
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
    supabase.table("profiles").delete().eq("id", profile_id).eq("user_id", user_id).execute()
    return {"status": "deleted"}


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
    supabase.storage.from_(AVATAR_BUCKET).upload(
        path, media.content, {"content-type": media.mime_type, "upsert": "true"}
    )
    public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)

    supabase.table("profiles").update({"avatar_url": public_url}).eq(
        "id", profile_id
    ).eq("user_id", user_id).execute()
    return {"avatar_url": public_url}
