"""Download limitado de imagens oficiais da Shopee, compartilhado pelos módulos.

Não aceita URL enviada pelo cliente: os endpoints obtêm a imagem do produto
autenticado no banco antes de chamar este módulo. Redirecionamentos são
revalidados contra uma lista estrita de CDNs para limitar SSRF.
"""

import logging
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException


logger = logging.getLogger(__name__)
SHOPEE_IMAGE_HOSTS = frozenset({
    "cf.shopee.com.br", "down-br.img.susercontent.com", "img.susercontent.com",
})
MAX_PRODUCT_IMAGE_BYTES = 8 * 1024 * 1024


def is_shopee_image_url(raw: str | None) -> bool:
    """HTTPS e host de imagem Shopee conhecido; sem credenciais nem porta atípica."""
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme == "https" and
                (host in SHOPEE_IMAGE_HOSTS or host.endswith(".img.susercontent.com")) and
                parsed.username is None and parsed.password is None and
                parsed.port in (None, 443))
    except (ValueError, TypeError):
        return False


def _check_shopee_image_url(raw: str) -> str:
    if not is_shopee_image_url(raw):
        raise HTTPException(status_code=400, detail="Origem da imagem Shopee não autorizada.")
    return raw


async def _download_shopee_image(raw_url: str) -> bytearray:
    """Baixa no máximo 8 MB; valida cada redirecionamento e não segue hosts externos."""
    url = _check_shopee_image_url(raw_url)
    async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=4), follow_redirects=False) as client:
        for _ in range(3):
            try:
                async with client.stream("GET", url, headers={"Accept": "image/jpeg,image/png,image/webp"}) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise HTTPException(status_code=502, detail="Imagem Shopee indisponível.")
                        url = _check_shopee_image_url(urljoin(url, location))
                        continue
                    if response.status_code != 200:
                        raise HTTPException(status_code=502, detail="Imagem Shopee indisponível.")
                    declared = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if declared and not declared.startswith("image/") and declared != "application/octet-stream":
                        raise HTTPException(status_code=415, detail="O produto não possui uma imagem compatível.")
                    try:
                        declared_size = int(response.headers.get("content-length", "0") or 0)
                    except ValueError:
                        raise HTTPException(status_code=502, detail="Resposta inválida do servidor de imagens.") from None
                    if declared_size > MAX_PRODUCT_IMAGE_BYTES:
                        raise HTTPException(status_code=413, detail="Imagem Shopee excede 8 MB.")
                    content = bytearray()
                    async for chunk in response.aiter_bytes(256 * 1024):
                        content.extend(chunk)
                        if len(content) > MAX_PRODUCT_IMAGE_BYTES:
                            raise HTTPException(status_code=413, detail="Imagem Shopee excede 8 MB.")
                    return content
            except httpx.HTTPError as exc:
                logger.warning("Falha ao importar imagem do CDN Shopee (%s)", type(exc).__name__)
                raise HTTPException(status_code=502, detail="Não foi possível acessar a foto Shopee.") from None
    raise HTTPException(status_code=502, detail="Redirecionamentos excessivos na imagem Shopee.")
