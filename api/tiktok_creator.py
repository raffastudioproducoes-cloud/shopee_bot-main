"""creator_info do TikTok para a tela de publicação e para validar escolhas.

Lê o token do dono do perfil (nunca o devolve), consulta o creator_info, renova
o token uma vez se expirou e mapeia só os campos públicos que a tela precisa.
"""
import logging

from fastapi import HTTPException

from . import tiktok_oauth
from .crypto import decrypt, encrypt
from .database import supabase
from .profiles import scope_owner
from .tiktok_options import TikTokPostOptions, check_against_creator

logger = logging.getLogger(__name__)

CANNOT_POST = {
    "spam_risk_too_many_posts": (
        "Esta conta TikTok atingiu o limite diário de publicações. Tente novamente mais tarde."
    ),
    "spam_risk_user_banned_from_posting": "Esta conta TikTok está impedida de publicar no momento.",
    "reached_active_user_cap": (
        "O app atingiu a cota diária de contas publicando no TikTok. Tente novamente mais tarde."
    ),
}
RECONNECT = "Autorização do TikTok expirada ou incompleta. Reconecte o TikTok em Credenciais."


def public_creator_info(data: dict, code: str = "ok") -> dict:
    """Somente o que a tela de publicação usa; sem token nem open_id."""
    return {
        "creator_nickname": data.get("creator_nickname") or "",
        "creator_username": data.get("creator_username") or "",
        "creator_avatar_url": data.get("creator_avatar_url") or "",
        "privacy_level_options": list(data.get("privacy_level_options") or []),
        "comment_disabled": bool(data.get("comment_disabled")),
        "duet_disabled": bool(data.get("duet_disabled")),
        "stitch_disabled": bool(data.get("stitch_disabled")),
        "max_video_post_duration_sec": data.get("max_video_post_duration_sec"),
        "can_post": code == "ok",
        "cannot_post_reason": CANNOT_POST.get(code),
    }


def _stored_tokens(user_id, profile_id) -> tuple[str, str | None]:
    row = (scope_owner(supabase.table("tiktok_credentials")
           .select("user_access_token, refresh_token"), user_id, profile_id)
           .maybe_single().execute())
    data = row.data if row and row.data else {}
    if not data.get("user_access_token"):
        raise HTTPException(status_code=409, detail="Conecte o TikTok em Credenciais antes de publicar.")
    refresh = data.get("refresh_token")
    return decrypt(data["user_access_token"]), decrypt(refresh) if refresh else None


async def _refreshed_token(user_id, profile_id, refresh_token: str | None) -> str:
    if not refresh_token or not tiktok_oauth.CLIENT_KEY or not tiktok_oauth.CLIENT_SECRET:
        raise HTTPException(status_code=409, detail=RECONNECT)
    try:
        tokens = await tiktok_oauth.refresh_access_token(refresh_token)
    except Exception as exc:
        logger.warning("TikTok creator_info: renovação falhou (%s)", type(exc).__name__)
        raise HTTPException(status_code=409, detail=RECONNECT) from None
    update = {"user_access_token": encrypt(tokens["access_token"])}
    if tokens.get("refresh_token"):
        update["refresh_token"] = encrypt(tokens["refresh_token"])
    scope_owner(supabase.table("tiktok_credentials").update(update), user_id, profile_id).execute()
    return tokens["access_token"]


async def load_creator_info(user_id, profile_id) -> dict:
    access_token, refresh_token = _stored_tokens(user_id, profile_id)
    try:
        code, data = await tiktok_oauth.query_creator_info(access_token)
        if code == "access_token_invalid":
            access_token = await _refreshed_token(user_id, profile_id, refresh_token)
            code, data = await tiktok_oauth.query_creator_info(access_token)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("TikTok creator_info indisponível (%s)", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Não foi possível consultar a conta TikTok agora.") from None
    if code in CANNOT_POST:
        return public_creator_info(data, code)
    if code in ("access_token_invalid", "scope_not_authorized"):
        raise HTTPException(status_code=409, detail=RECONNECT)
    if code == "rate_limit_exceeded":
        raise HTTPException(status_code=429, detail="Muitas consultas ao TikTok. Aguarde um minuto.")
    if code != "ok" or not data.get("privacy_level_options"):
        raise HTTPException(status_code=502, detail="Não foi possível consultar a conta TikTok agora.")
    return public_creator_info(data)


async def require_allowed_choice(options: TikTokPostOptions, user_id, profile_id) -> None:
    """Confere a escolha com o creator_info atual antes de gravar o post.

    O rascunho (video.upload) não tem privacidade nem interações a conferir:
    o usuário finaliza no app do TikTok.
    """
    if options.mode != "direct":
        return
    creator = await load_creator_info(user_id, profile_id)
    if not creator["can_post"]:
        raise HTTPException(status_code=409, detail=creator["cannot_post_reason"])
    try:
        check_against_creator(options, creator)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
