"""Host único da Open Platform usado pelo cliente Shopee Vídeo e pelo OAuth.

Módulo sem dependências: importável pela API nova (`from apis...`) e pelo
scheduler (`from shopee_bot.apis...`). Não há confirmação oficial do host
regional do Brasil; o padrão é o host global de parceiros, sobrescrevível por
SHOPEE_VIDEO_API_BASE_URL / SHOPEE_VIDEO_SANDBOX_API_BASE_URL (a confirmar no
primeiro teste real). Só domínios Shopee em HTTPS, sem porta, caminho ou
credencial na URL, para a variável nunca virar SSRF.
"""

import os
from urllib.parse import urlsplit

LIVE_DEFAULT = "https://openplatform.shopee.com.br"  # Brasil (o código vem de open.shopee.com.br)
SANDBOX_DEFAULT = "https://partner.test-stable.shopeemobile.com"
ALLOWED_DOMAINS = ("shopeemobile.com", "shopee.com.br", "shopee.com", "shopee.sg")


def _validated(url: str) -> str:
    base = url.strip().rstrip("/")
    parts = urlsplit(base)
    hostname = (parts.hostname or "").lower()
    allowed = any(hostname == d or hostname.endswith("." + d) for d in ALLOWED_DOMAINS)
    if (parts.scheme != "https" or not allowed or parts.port is not None
            or parts.username or parts.password or parts.path or parts.query or parts.fragment):
        raise ValueError("Host da API Shopee Vídeo inválido: use https em domínio Shopee.")
    return base


def api_base_url(*, sandbox: bool) -> str:
    """URL base (sem barra final) para chamadas /api/v2/* da Shopee Vídeo."""
    env = "SHOPEE_VIDEO_SANDBOX_API_BASE_URL" if sandbox else "SHOPEE_VIDEO_API_BASE_URL"
    return _validated(os.environ.get(env) or (SANDBOX_DEFAULT if sandbox else LIVE_DEFAULT))
