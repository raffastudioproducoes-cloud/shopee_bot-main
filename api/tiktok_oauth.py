"""
OAuth do TikTok (TikTok for Developers) — API Python (FastAPI).

Duplica as funções OAuth puras de `apis/tiktok.py` (mesmas URLs, mesmos
parâmetros) em vez de importar entre módulos — mesmo padrão já usado
neste projeto pra código compartilhado entre o Flask antigo e a API nova
(ver docstring de api/threads_oauth.py e api/crypto.py). Evita que a API
nova dependa de `shopee_bot.utils` (as funções de POST de vídeo de
`apis/tiktok.py` usam `retry_with_backoff`; as de OAuth aqui, não).

App único da plataforma (mesmo padrão de api/threads_oauth.py): Rafa
registra UM app no TikTok for Developers, Client Key/Secret vêm de env
(TIKTOK_CLIENT_KEY/TIKTOK_CLIENT_SECRET) — usuário final só clica
"Conectar TikTok" e autoriza, nunca vê nem cola Client Key/Secret de
app nenhum. Antes disso cada usuário cadastrava o próprio app
(per-user); migrado pro app único pra simplificar pro usuário leigo
(decisão + rollout documentados no vault, ver
Projetos/ShopeeAutoVendas/27-Migracao-App-Unico-OAuth.md).

Só o essencial pro fluxo de login (authorize URL, troca de code por
token). Publicação de vídeo (Content Posting API) continua exclusiva do
Flask por enquanto — ver apis/tiktok.py::post_video.
"""

import os
from urllib.parse import quote

import httpx

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
CALLBACK_URL = os.environ.get("TIKTOK_CALLBACK_URL")
CLIENT_KEY = (os.environ.get("TIKTOK_CLIENT_KEY") or "").strip() or None
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET")
DEFAULT_SCOPE = os.environ.get(
    "TIKTOK_PERMISSIONS", "user.info.basic,video.publish,video.upload"
)


class TikTokOAuthError(Exception):
    pass


def _callback_url() -> str:
    return (CALLBACK_URL or "").rstrip("/") + "/"


def get_user_auth_url(state: str) -> str:
    # https://developers.tiktok.com/doc/login-kit-web
    #
    # `state` é ecoado pelo TikTok de volta no /callback — usado pelo
    # router (api/routers/credentials.py) pra CSRF binding do
    # account-linking (evita que um atacante induza a vítima a linkar a
    # conta social DELE à conta da vítima).
    return (
        f"{AUTH_URL}?client_key={CLIENT_KEY}"
        f"&scope={quote(DEFAULT_SCOPE, safe=',')}"
        "&response_type=code"
        f"&redirect_uri={quote(_callback_url(), safe='')}"
        f"&state={quote(state, safe='')}"
    )


async def get_user_auth_id_token(code: str) -> tuple[str, str | None, str]:
    """Troca code por (access_token, refresh_token, open_id).

    https://developers.tiktok.com/doc/oauth-user-access-token-management
    """
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            TOKEN_URL,
            data={
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _callback_url(),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if res.status_code != 200:
        raise TikTokOAuthError(
            f"Failed to Get User Access Token: {res.status_code} {res.text}"
        )

    data = res.json()
    if "access_token" not in data:
        raise TikTokOAuthError(f"TikTok OAuth Error: {data}")

    return data["access_token"], data.get("refresh_token"), data["open_id"]
