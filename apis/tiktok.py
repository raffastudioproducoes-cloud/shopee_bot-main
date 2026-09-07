"""
TikTok API via TikTok for Developers (v2).

Schema de credenciais:
  - app_id: Client Key
  - secret: Client Secret
  - (Opcional futuro) user_access_token: via OAuth Authorization Code flow ou
    ser fornecido pelo usuário.

Nota:
  - TikTok só suporta publicar videos (não texto puro) via API oficial.
  - post_text disponível aqui retorna NotImplementedError com orientação.
  - validate_credentials testa o Client Key/Secret via webhook/event ou
    oauth/token se disponível; hoje a documentação permite validar via
    POST /oauth/token?grant_type=client_credentials com client_key/client_secret.
"""

import os
import time
import requests
from shopee_bot.utils import retry_with_backoff

API_BASE = "https://open.tiktok.com/open_api/v2"  # placeholder base
TOKENS_BASE = "https://open.tiktok.com/api/v2"     # gráfico tokens
# Nota: endpoints reais precisam de consulta à dokumentasi atual da TikTok
# Developers pois eles mudam com frequência.
# Versão mínima funcional: validação via oauth/client_credentials e post de
# video se disponível (não implementado aqui).

def _client_credentials_token(client_key, client_secret, _cache={}):
    """Obtém token via OAuth Client Credentials (se disponível na API)."""
    raise NotImplementedError(
        "TikTok: Client Credentials token flow não implementado. "
        "A TikTok API paga/foca em Authorization Code flow. "
        "Ver documentação: https://developers.tiktok.com/doc/oauth-overview "
        "e https://developers.tiktok.com/doc/seamless-sharing"
    )

def validate_credentials(app_id, secret):
    """Valida as credenciais TikTok.

    A TikTok não expõe um endpoint público de 'validar credencial' bruta
    com client_key/secret sem OAuth user-level. Implementamos validação
    mínima chamando oauth/token se disponível; hoje levantamos
    NotImplementedError para indicar que a validação completa depende
    do flow (authorization code com user).

    Plano alternativo: usar webhook/event debug para testar se o app existe.
    """
    raise NotImplementedError(
        "TikTok: validação de credenciais (client_key/client_secret) "
        "não disponível via API pública sem OAuth user flow. "
        "O usuário deve fornecer um user_access_token via OAuth Authorization "
        "Code flow para publicar. Ver: "
        "https://developers.tiktok.com/doc/getting-started-guide "
        "e https://developers.tiktok.com/doc/uni-app-access-token"
    )

def post_text(app_id, secret, text):
    """Não suportado nativamente pela TikTok.

    A TikTok é uma rede de vídeos; postar textos puros sem thumb/video
    não é possível via API oficial.
    """
    raise NotImplementedError(
        "TikTok: post_text não suportado. A TikTok requer um vídeo para "
        "postagem via API. Postar um texto puro não é funcional na plataforma. "
        "Para publicar, use post_video com um arquivo ou URL de vídeo."
    )

def post_video(app_id, secret, video_url_or_path, text):
    """Publica um vídeo no TikTok.

    Cautela: requer user_access_token (não implementado aqui). Se o tempo
    permitir, implementar upload + publish com:
      1. Obter upload URL via endpoint de upload
      2. Upload do video (chunked ou direto)
      3. Publicar o video task

    Hoje levantamos NotImplementedError com orientação.
    """
    raise NotImplementedError(
        "TikTok: post_video não implementado. Requer OAuth user_access_token "
        "e flow de upload/publish de video via TikTok for Developers API. "
        "Ver: https://developers.tiktok.com/doc/video-upload-grade-v2 "
        "e https://developers.tiktok.com/doc/post-video-task-v2"
    )

def post_product(app_id, secret, product):
    """Não suportado (video é necessário).

    A TikTok é uma rede de vídeos; produtores de afiliados costumam
    criar vídeos curtos com link de afiliado no description/bio.
    """
    raise NotImplementedError(
        "TikTok: post_product não suportado via API oficial sem um video "
        "upload/publish flow implementado. A TikTok não aceita posts de texto "
        "com link de afiliado diretamente."
    )
