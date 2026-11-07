"""Links Shopee por afiliado, independentes da chave usada para consultar ofertas.

O `an_redir` é documentado pela Shopee para parceiros/encurtadores. O link
original é higienizado antes de adicionar a identidade da conta do cliente.
"""

import re
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit


_AFFILIATE_ID = re.compile(r"[0-9]{5,20}\Z")
_SHOP_HOSTS = frozenset({"shopee.com.br", "www.shopee.com.br"})
_REDIRECT_HOSTS = frozenset({"s.shopee.com.br", "shopee.com.br", "www.shopee.com.br"})


def valid_affiliate_id(value: str | None) -> bool:
    return bool(value and _AFFILIATE_ID.fullmatch(value))


def canonical_product_url(value: str | None) -> str | None:
    """Somente HTTPS Shopee Brasil; remove tracking prévio, fragmento e auth.

    Não resolve links curtos via rede (proteção contra SSRF). O catálogo traz
    `productLink`, já a URL de produto original, que é a fonte obrigatória.
    """
    if not value or len(value) > 2048:
        return None
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or (url.hostname or "").lower() not in _SHOP_HOSTS
                or url.username or url.password or url.port not in (None, 443)
                or not url.path or url.path == "/"):
            return None
        return urlunsplit(("https", url.hostname.lower(), url.path, "", ""))
    except (ValueError, TypeError):
        return None


def affiliate_id_from_link(value: str | None) -> str | None:
    """Extrai o ID de um link *expandido*, sem consultar URLs arbitrárias.

    Links opacos `s.shopee.com.br/ABC` precisam ser expandidos pela própria
    conta Shopee antes da importação; nunca inferir ID de um código curto.
    """
    if not value or len(value) > 4096:
        return None
    if valid_affiliate_id(value.strip()):
        return value.strip()
    try:
        parsed = urlsplit(value.strip())
        if (parsed.scheme != "https" or (parsed.hostname or "").lower() not in _REDIRECT_HOSTS
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            return None
        query = parse_qs(parsed.query)
        for value in query.get("affiliate_id", []):
            if valid_affiliate_id(value):
                return value
        for value in query.get("utm_source", []):
            if value.startswith("an_") and valid_affiliate_id(value[3:]):
                return value[3:]
    except (ValueError, TypeError):
        pass
    return None


def build_affiliate_link(product_url: str | None, affiliate_id: str | None) -> str | None:
    original = canonical_product_url(product_url)
    if not original or not valid_affiliate_id(affiliate_id):
        return None
    return ("https://s.shopee.com.br/an_redir?origin_link="
            f"{quote(original, safe='')}&affiliate_id={affiliate_id}")


def personalize_product(product: dict, affiliate_id: str | None) -> dict:
    """Recalcula na resposta o link Shopee de produtos legados já salvos.

    Nunca devolve o antigo `commission_link` do administrador quando a origem
    é um produto oficial da Shopee. Produtos de outras origens não são alterados.
    """
    original = product.get("original_link")
    if canonical_product_url(original):
        return {**product, "commission_link": build_affiliate_link(original, affiliate_id) or ""}
    return product
