"""
TikTok API via TikTok for Developers (Content Posting API v2).

BLOQUEIO EXTERNO CONHECIDO (fora do nosso controle, não é motivo pra não
implementar):
  A TikTok exige aprovação/audit de parceiro pra o modo "Direct Post"
  (publicar direto no perfil do usuário) funcionar em produção pra contas
  que não sejam testers cadastrados no app. Sem essa aprovação, a Content
  Posting API só publica em modo rascunho/inbox e só pro dono do app /
  testers de sandbox — mais rígido que o processo de review da Meta.
  O código abaixo chama o endpoint de "Direct Post" (/v2/post/publish/
  video/init/) e usa privacy_level=SELF_ONLY por padrão, que é o nível
  aceito mesmo sem aprovação (publica como privado/rascunho pro próprio
  dono da conta autorizada). Ver:
  https://developers.tiktok.com/doc/content-posting-api-get-started
  https://developers.tiktok.com/doc/content-posting-api-reference-direct-post

Schema de credenciais (tabela tiktok_credentials):
  - app_id: Client Key global do aplicativo SaaS (configurado só no servidor).
  - secret: Client Secret global, também só no servidor.
  - user_access_token / refresh_token / open_id: obtidos via OAuth
    Authorization Code depois que o usuário autoriza o app (ver
    get_user_auth_url / get_user_auth_id_token abaixo, e o espelho async
    em api/tiktok_oauth.py usado pelo router FastAPI).

Fluxo OAuth (TikTok Login Kit, Authorization Code):
  1. get_user_auth_url(client_key, redirect_uri) -> usuário autoriza no
     navegador.
  2. TikTok redireciona pra redirect_uri com ?code=...
  3. get_user_auth_id_token(client_key, client_secret, code, redirect_uri)
     troca o code por access_token/refresh_token/open_id.
  4. refresh_user_token(...) quando o access_token expirar (~24h; o
     refresh_token dura ~365 dias).

post_video usa a Content Posting API (Direct Post):
  1. POST /v2/post/publish/video/init/ -> publish_id + upload_url.
  2. PUT do arquivo de vídeo pra upload_url.
  3. Poll em /v2/post/publish/status/fetch/ até status virar
     PUBLISH_COMPLETE (ou FAILED).

TODO: upload em múltiplos chunks pra vídeos grandes — hoje só sobe o
arquivo inteiro num chunk único (funciona pra vídeos curtos de afiliado;
a TikTok pede chunk_size entre 5MB-64MB pra arquivos maiores). Ver
https://developers.tiktok.com/doc/content-posting-api-reference-direct-post

Photo Direct Post fica pendente de uma tela que consulte Creator Info e mostre
as opções de privacidade exigidas pelo TikTok, além de URL pública em domínio
ou prefixo verificado. Não tratar uma imagem enviada localmente como pronta
para publicação no TikTok.
"""

import os
import time
from urllib.parse import quote

import requests

from shopee_bot.utils import ConnectionTestError, retry_with_backoff

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
POST_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
POST_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

DEFAULT_SCOPE = "user.info.basic,video.publish,video.upload"


class TikTokAPIError(Exception):
    pass


def _raise_exception(err_text, res, url):
    raise TikTokAPIError(
        "{0}:\nStatus: {1}\nURL: {2}\nText: {3}".format(
            err_text, res.status_code, url, res.text
        )
    )


###
# OAuth (Authorization Code) — TikTok Login Kit
###
def get_user_auth_url(client_key, redirect_uri, scope=DEFAULT_SCOPE, state=None):
    """URL de autorização do TikTok Login Kit.

    https://developers.tiktok.com/doc/login-kit-web
    """
    url = (
        f"{AUTH_URL}?client_key={client_key}"
        f"&scope={quote(scope, safe=',')}"
        "&response_type=code"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
    )
    if state:
        url += f"&state={quote(state, safe='')}"
    return url


def get_user_auth_id_token(client_key, client_secret, code, redirect_uri):
    """Troca o `code` do callback por access_token/refresh_token/open_id.

    https://developers.tiktok.com/doc/oauth-user-access-token-management
    """
    res = retry_with_backoff(
        requests.post,
        TOKEN_URL,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if res.status_code != 200:
        _raise_exception("Failed to Get User Access Token", res, TOKEN_URL)

    data = res.json()
    if "access_token" not in data:
        _raise_exception(f"TikTok OAuth Error: {data}", res, TOKEN_URL)

    return data["access_token"], data.get("refresh_token"), data["open_id"]


def refresh_user_token(client_key, client_secret, refresh_token):
    """Renova o access_token (válido ~24h) usando o refresh_token (~365 dias).

    https://developers.tiktok.com/doc/oauth-user-access-token-management
    """
    res = retry_with_backoff(
        requests.post,
        TOKEN_URL,
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if res.status_code != 200:
        _raise_exception("Failed to Refresh User Access Token", res, TOKEN_URL)
    return res.json()


def get_user_info(user_access_token, fields="open_id,display_name"):
    res = retry_with_backoff(
        requests.get,
        USER_INFO_URL,
        params={"fields": fields},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    if res.status_code != 200:
        _raise_exception("Failed to Get User Info", res, USER_INFO_URL)
    return res.json()["data"]["user"]


def validate_credentials(app_id, secret):
    """Valida as credenciais TikTok.

    A TikTok não expõe um endpoint de 'validar client_key/client_secret'
    isolado sem OAuth user-level — o único jeito de confirmar que um
    Client Key/Secret funcionam de verdade é completar o Authorization
    Code flow (ver get_user_auth_url/get_user_auth_id_token) e checar se
    a troca de code por token não falha por invalid_client.

    TODO: chamar isso a partir do callback OAuth (api/routers/
    credentials.py::tiktok_callback) marcando a credencial como validada
    só depois de um get_user_auth_id_token bem-sucedido — hoje o save
    simples (PUT /credentials/tiktok) grava app_id/secret sem validar
    contra a API, igual o Threads fazia antes do OAuth existir.
    """
    raise NotImplementedError(
        "TikTok: validação de client_key/client_secret sem OAuth user "
        "flow não é suportada pela API. Complete o fluxo de autorização "
        "(GET /credentials/tiktok/authorize) pra validar de verdade."
    )


_USER_INFO_ERRORS = {
    "access_token_invalid": (
        "Autorização do TikTok inválida ou expirada  verifique o app do "
        "TikTok (sandbox/Target Users) e reconecte"
    ),
    "scope_not_authorized": (
        "O TikTok não autorizou o escopo user.info.basic  verifique o app "
        "(Login Kit, sandbox/Target Users) e reconecte"
    ),
    "rate_limit_exceeded": "Limite de requisições do TikTok atingido  tente mais tarde",
}


def _user_info(access_token):
    res = retry_with_backoff(
        requests.get,
        USER_INFO_URL,
        params={"fields": "open_id,display_name"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        body = res.json() or {}
    except ValueError:
        body = {}
    code = (body.get("error") or {}).get("code") or ""
    return res, code, body


def validate_user_token(client_key, client_secret, access_token, refresh_token=None):
    """Valida o token do USUÁRIO com /v2/user/info/ (escopo user.info.basic).

    Traduz o `error.code` do corpo (o HTTP 401 sozinho não diz a causa) e,
    em access_token_invalid, renova com o refresh_token e repete uma vez.
    Retorna (usuário, tokens renovados ou None); em falha levanta
    ConnectionTestError sem token, com `refreshed` se já renovou."""
    refreshed = None
    res, code, body = _user_info(access_token)
    if code == "access_token_invalid" and refresh_token:
        try:
            refreshed = refresh_user_token(client_key, client_secret, refresh_token)
            if not refreshed.get("access_token"):
                raise ValueError("sem access_token")
        except Exception:
            raise ConnectionTestError(
                "Token do TikTok expirado e a renovação falhou  reconecte"
            )
        res, code, body = _user_info(refreshed["access_token"])
    if res.status_code == 200 and code in ("", "ok"):
        user = (body.get("data") or {}).get("user")
        if user:
            return user, refreshed
        raise ConnectionTestError("Resposta inesperada do TikTok ao validar o token", refreshed)
    message = _USER_INFO_ERRORS.get(code) or (
        f"O TikTok recusou a verificação (status {res.status_code}"
        + (f", código {code}" if code else "") + ")"
    )
    raise ConnectionTestError(message, refreshed)


def post_text(app_id, secret, text):
    """Não suportado nativamente pela TikTok.

    A TikTok é uma rede de vídeos; postar textos puros sem vídeo não é
    possível via API oficial.
    """
    raise NotImplementedError(
        "TikTok: post_text não suportado. A TikTok requer um vídeo para "
        "postagem via API. Para publicar, use post_video com um arquivo "
        "de vídeo."
    )


###
# Content Posting API — Direct Post
###
def _init_video_post(user_access_token, video_size, text, privacy_level):
    payload = {
        "post_info": {
            "title": text or "",
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        },
    }
    res = retry_with_backoff(
        requests.post,
        POST_INIT_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    if res.status_code != 200:
        _raise_exception("Failed to Init Video Post", res, POST_INIT_URL)

    data = res.json()["data"]
    return data["publish_id"], data["upload_url"]


def _upload_video_file(upload_url, video_path):
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    video_size = len(video_bytes)

    # ponytail: chunk único (arquivo inteiro) — upload em múltiplos
    # chunks fica pro TODO no topo do módulo, se vídeos > 64MB virarem
    # necessidade real.
    res = requests.put(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
    )
    if res.status_code not in (200, 201):
        _raise_exception("Failed to Upload Video File", res, upload_url)


def _wait_publish_complete(user_access_token, publish_id, timeout_s=120):
    # https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        res = retry_with_backoff(
            requests.post,
            POST_STATUS_URL,
            json={"publish_id": publish_id},
            headers={
                "Authorization": f"Bearer {user_access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
        )
        if res.status_code != 200:
            _raise_exception("Failed to Fetch Post Status", res, POST_STATUS_URL)

        data = res.json()["data"]
        status = data.get("status")

        if status == "PUBLISH_COMPLETE":
            return data
        if status == "FAILED":
            raise TikTokAPIError(
                f"TikTok post {publish_id} failed: {data.get('fail_reason')}"
            )
        time.sleep(2)

    raise TikTokAPIError(
        f"TikTok post {publish_id} did not finish within {timeout_s}s"
    )


def post_video(user_access_token, video_path, text, privacy_level="SELF_ONLY"):
    """Publica um vídeo no TikTok via Content Posting API (Direct Post).

    `video_path` precisa ser um arquivo local temporário preparado pelo
    chamador; a origem persistente de mídias é o Supabase Storage.
    `privacy_level` default é SELF_ONLY porque contas sem aprovação de
    parceiro da TikTok só conseguem publicar assim — ver bloqueio no
    topo do módulo. Trocar pra PUBLIC_TO_EVERYONE só depois que o app
    estiver auditado pela TikTok.

    Retorna o publish_id.
    """
    video_size = os.path.getsize(video_path)
    publish_id, upload_url = _init_video_post(
        user_access_token, video_size, text, privacy_level
    )
    _upload_video_file(upload_url, video_path)
    _wait_publish_complete(user_access_token, publish_id)
    return publish_id


def post_product(app_id, secret, product):
    """Não suportado (vídeo é necessário).

    A TikTok é uma rede de vídeos; produtores de afiliados costumam
    criar vídeos curtos com link de afiliado no description/bio. Postar
    um produto sem vídeo associado não é possível via API oficial.
    """
    raise NotImplementedError(
        "TikTok: post_product não suportado via API oficial sem um "
        "vídeo associado. Use post_video com um arquivo de vídeo."
    )
