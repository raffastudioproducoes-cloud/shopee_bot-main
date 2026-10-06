"""
Profiles Router — API Python (FastAPI)

CRUD de perfis (multi-profile) e troca de perfil ativo (`/profiles/{id}/activate`).
"""

import logging

import fleep
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel

from ..database import supabase
from ..profiles import PROFILE_LIMIT, can_create_profile, is_principal
from .auth import (
    _check_login_rate_limit,
    _create_token,
    _decode_token,
    _get_user_from_supabase,
    _password_version,
    get_current_user_id,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])
logger = logging.getLogger(__name__)

# Mesmo padrão de validação por magic-byte de api/routers/posts.py
# (fleep.get + checagem de qualquer mime detectado contra a allowlist).
# Mapeado pra extensão pra fixar o nome do arquivo no bucket e evitar
# path traversal via file.filename (perfil so tem 1 avatar por vez).
ALLOWED_AVATAR_MIMES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
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


def _resolve_profile_id(profile_id: str, user_id: str) -> str | None:
    """Confirma que o perfil do token pertence ao usuário (perfil excluído
    ou de outra conta não vale). Se não pertencer, cai no perfil principal
    do usuário; sem principal, None (sem filtro por perfil)."""
    owned = (
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
    """Claim opcional -- token emitido antes desta feature não tem profile_id."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    profile_id = payload.get("profile_id")
    if not profile_id:
        return None
    return _resolve_profile_id(profile_id, user_id)


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
    if not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    return existing.data


@router.get("")
async def list_profiles(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return result.data


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

    info = fleep.get(content[:128])
    matched_mime = next((m for m in info.mime if m in ALLOWED_AVATAR_MIMES), None)
    if not matched_mime:
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem válida.")

    path = f"{profile_id}/avatar{ALLOWED_AVATAR_MIMES[matched_mime]}"
    supabase.storage.from_(AVATAR_BUCKET).upload(
        path, content, {"content-type": matched_mime, "upsert": "true"}
    )
    public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)

    supabase.table("profiles").update({"avatar_url": public_url}).eq(
        "id", profile_id
    ).eq("user_id", user_id).execute()
    return {"avatar_url": public_url}
