"""
OAuth do TikTok (TikTok for Developers) — API Python (FastAPI).

Duplica as funções OAuth puras de `apis/tiktok.py` (mesmas URLs, mesmos
parâmetros) em vez de importar entre módulos — mesmo padrão já usado
neste projeto pra código compartilhado entre o Flask antigo e a API nova
(ver docstring de api/threads_oauth.py e api/crypto.py). Evita que a API
nova dependa de `shopee_bot.utils` (as funções de POST de vídeo de
`apis/tiktok.py` usam `retry_with_backoff`; as de OAuth aqui, não).

Diferença importante em relação ao Threads: o Client Key/Secret do
TikTok não é um único app global (THREADS_APP_ID/SECRET via env) — cada
usuário cadastra seu próprio app no TikTok for Developers e já salvou
Client Key/Secret via PUT /credentials/tiktok (tabela tiktok_credentials,
colunas app_id/secret). Por isso as funções aqui recebem client_key/
client_secret como parâmetro, puxados da credencial do usuário no
router, em vez de ler de variável de ambiente.

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
DEFAULT_SCOPE = os.environ.get(
    "TIKTOK_PERMISSIONS", "user.info.basic,video.publish,video.upload"
)


class TikTokOAuthError(Exception):
    pass


def get_user_auth_url(client_key: str, state: str) -> str:
    # https://developers.tiktok.com/doc/login-kit-web
    #
    # `state` é ecoado pelo TikTok de volta no /callback — usado pelo
    # router (api/routers/credentials.py) pra CSRF binding do
    # account-linking (evita que um atacante induza a vítima a linkar a
    # conta social DELE à conta da vítima).
    return (
        f"{AUTH_URL}?client_key={client_key}"
        f"&scope={quote(DEFAULT_SCOPE, safe=',')}"
        "&response_type=code"
        f"&redirect_uri={quote(CALLBACK_URL or '', safe='')}"
        f"&state={quote(state, safe='')}"
    )


async def get_user_auth_id_token(
    client_key: str, client_secret: str, code: str
) -> tuple[str, str | None, str]:
    """Troca code por (access_token, refresh_token, open_id).

    https://developers.tiktok.com/doc/oauth-user-access-token-management
    """
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.post(
            TOKEN_URL,
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": CALLBACK_URL,
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
