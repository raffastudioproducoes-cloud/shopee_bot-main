"""
Kwai API (https://kw.ai / developer.kwai.com).

Status atual da API Kwai:
  - A plataforma Kwai brasileira não disponibiliza uma API pública documentada
    para criação de posts automáticos (texto/vídeo com link de afiliado).
  - Existe API para parceiros/Advertisers para gestão de campanhas, mas não
    há documentação pública de como postar no feed do usuário via API.
  - Esta implementação levanta NotImplementedError com orientação do que
    faltaria para integrar, já que o usuário pode adquirir acesso posterior.

Se o usuário tiver acesso a API regia de Kwai (parceiro), esta é a entrada
para implementar.
"""

import os
import time
import requests
from shopee_bot.utils import retry_with_backoff

API_BASE = "https://api.kw.ai"  # placeholder

def validate_credentials(app_id, secret):
    """Valida as credenciais Kwai.

    Hoje não há endpoint público documentado para validar app_id/secret
    de Kwai para postagem. Implementamos um placeholder que levanta
    NotImplementedError com documentação.
    """
    raise NotImplementedError(
        "Kwai: não há API pública documentada para validar credenciais "
        "de postagem. A Kwai disponibiliza API de parceiros/Advertisers "
        "para gestão de campanhas, mas não há documentação pública de como "
        "postar no feed do usuário via API. Verificar em: "
        "https://kw.ai e https://developer.kwai.com (se disponível)."
    )

def post_text(app_id, secret, text):
    """Não suportado.

    Sem API pública para postar texto no feed do Kwai.
    """
    raise NotImplementedError(
        "Kwai: não há API pública documentada para postar texto no feed do "
        "usuário. A plataforma funciona via app mobile e não disponibiliza "
        "endpoints públicos para postagem automática (como X/Twitter ou Meta)."
    )

def post_product(app_id, secret, product):
    """Não suportado.

    Requer API de postagem que não está documentada publicamente.
    """
    raise NotImplementedError(
        "Kwai: post_product não suportado. A Kwai não disponibiliza API "
        "pública documentada para postagem de conteúdo via programação. "
        "Para integração automática, o usuário precisaria de acesso à API "
        "de parceiros/Advertisers ou de um agregador de redes sociais que "
        "suporte Kwai (ex: Buffer, Hootsuite, etc. - verificar suporte real)."
    )
