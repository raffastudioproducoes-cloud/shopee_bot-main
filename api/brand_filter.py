"""Filtro da marca "Shopee" em texto que o site publica nas redes do usuário.

Regra do programa de Afiliados Shopee: não usar o logo nem a palavra "Shopee"
no nome das redes sociais ou sites. O texto gerado por IA, por modelo do site
ou vindo do produto passa por aqui antes de publicar. Links (https://..., www.,
shope.ee/..., shopee.com.br/...) são preservados: o link de afiliado é
necessário e não é nome de rede/site.

A troca é sempre mais curta que o original ("loja"), então o texto nunca
estoura o limite de caracteres de uma rede por causa do filtro.
"""

import re

NEUTRAL_WORD = "loja"

# Instrução permanente para todo prompt que gera texto publicável.
BRAND_RULE = (
    'NUNCA escreva a palavra "Shopee" (nem "shopee", "#shopee", "Shopee Vídeo" ou '
    "variações), nem cite o logo. Para falar da origem use termos neutros como "
    '"loja online", "marketplace", "o link" ou "oferta".'
)

_LINK = (
    r"(?:https?://|www\.)\S+"
    r"|(?:[\w-]+\.)*(?:shope\.ee|shopee\.com(?:\.br)?)/\S*"
)
_NAME = r"shop[eé]e"
# Hashtag com a marca some inteira (com o espaço que a antecede).
_HASHTAG = rf"[ \t]*[#＃]\w*{_NAME}\w*"
_WORD = rf"{_NAME}(?:[ \t]+v[ií]deo)?"
_TOKEN_RE = re.compile(
    rf"(?P<link>{_LINK})|(?P<tag>{_HASHTAG})|(?P<word>{_WORD})", re.IGNORECASE
)
_SENTENCE_START_RE = re.compile(r"(?:^|[.!?:][ \t]+|\n[ \t]*)$")


def _replace(text: str):
    def swap(match: re.Match) -> str:
        if match.group("link"):
            return match.group(0)
        if match.group("tag"):
            return ""
        word = match.group("word")
        starts = _SENTENCE_START_RE.search(text[:match.start()]) is not None
        return NEUTRAL_WORD.capitalize() if starts and word[0].isupper() else NEUTRAL_WORD

    return _TOKEN_RE.sub(swap, text)


def mentions_brand(text) -> bool:
    """Há a palavra "Shopee" fora de links?"""
    return isinstance(text, str) and any(
        m.group("tag") or m.group("word") for m in _TOKEN_RE.finditer(text)
    )


def strip_brand(text):
    """Texto sem a marca; sem ocorrência devolve o mesmo objeto (idempotente)."""
    if not mentions_brand(text):
        return text
    cleaned = _replace(text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"[ \t]+(?=\n|$)", "", cleaned)
    return re.sub(r"^[ \t]+", "", cleaned) if not text[:1].isspace() else cleaned
