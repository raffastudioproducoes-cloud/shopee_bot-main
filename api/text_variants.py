"""
Geração de descrição individual por rede, com uma solicitação de IA.

Cada rede escolhida recebe uma versão própria, respeitando limites reais de
caracteres, links, hashtags e menções. Se a IA falhar na segunda tentativa,
uma adaptação determinística preserva o link e gera texto válido e revisável.
"""

import json
import re

from .network_limits import _URL_RE, _HASHTAG_RE, _MENTION_RE

from .network_limits import NETWORK_RULES, validate_post

# Teto recomendável de uma copy de vendas (mesmo do Instagram/TikTok).
PRACTICAL_MAX_CHARS = 2200
# Variantes em JSON + raciocínio dos modelos que "pensam" (ver apis/llm.py).
VARIANTS_MAX_TOKENS = 4096

_TEXT_LIMIT_KEYS = (("max_hashtags", "hashtag(s)"), ("max_links", "link(s)"), ("max_mentions", "@menções"))


def effective_limit(network: str) -> int:
    return min(NETWORK_RULES[network]["max_chars"], PRACTICAL_MAX_CHARS)


def plan_variants(networks: list[str]) -> list[dict]:
    """Uma versão por rede; a maior capacidade aparece primeiro.

    Sem rede selecionada, mantém a variante genérica legada para a API.
    """
    chosen = [n for n in NETWORK_RULES if n in set(networks)]
    if not chosen:
        return [{"key": str(PRACTICAL_MAX_CHARS), "max_chars": PRACTICAL_MAX_CHARS, "networks": []}]
    return [
        {"key": n, "max_chars": effective_limit(n), "networks": [n]}
        for n in sorted(chosen, key=lambda net: -effective_limit(net))
    ]


def variant_issues(variant: dict, text: str) -> list[str]:
    """Erros de texto do variant em CADA rede do grupo (contagem de cada uma)."""
    if not variant["networks"]:
        n = len(text)
        return [f"texto máx. {variant['max_chars']} caracteres (você tem {n})"] if n > variant["max_chars"] else []
    msgs = []
    for net in variant["networks"]:
        msgs += [i["message"] for i in validate_post(net, [text], [], 0, False) if i["level"] == "error"]
    # teto prático só onde ele é mais baixo que a própria regra (Facebook)
    own_min = min(NETWORK_RULES[n]["max_chars"] for n in variant["networks"])
    if variant["max_chars"] < own_min and len(text) > variant["max_chars"]:
        msgs.append(f"texto máx. {variant['max_chars']} caracteres (você tem {len(text)})")
    return msgs


def _limit_line(variant: dict) -> str:
    rules = [NETWORK_RULES[n] for n in variant["networks"]]
    names = ", ".join(r["label"] for r in rules) or "redes sociais"
    line = f'- "{variant["key"]}" ({names}): no máximo {variant["max_chars"]} caracteres'
    if any(r["count"] == "weighted" for r in rules):
        line += " contados como no X (cada link conta 23 e cada emoji conta 2)"
    extras = []
    for key, label in _TEXT_LIMIT_KEYS:
        caps = [r[key] for r in rules if key in r]
        if caps:
            extras.append(f"no máximo {min(caps)} {label}")
    return line + (f"; {', '.join(extras)}" if extras else "") + "."


def build_prompt(product: dict, persona: str, variants: list[dict]) -> str:
    from apis.llm import PERSONA_TONES

    tone = PERSONA_TONES.get(persona, PERSONA_TONES["casual"])
    link = product.get("commission_link") or product.get("original_link") or ""
    shape = ", ".join(f'"{v["key"]}": "texto"' for v in variants)
    return (
        "Você escreve descrições comerciais para afiliados Shopee, em português do Brasil. "
        f"Tom: {tone}.\n"
        f"Crie {len(variants)} versão(ões) diferentes para o MESMO produto, "
        "uma por rede social selecionada. Preserve informações verdadeiras do produto "
        "e adapte linguagem, ritmo e chamada para ação à plataforma.\n"
        + "\n".join(_limit_line(v) for v in variants) + "\n\n"
        f"Produto: {product.get('name', '')}\n"
        f"Comissão: {product.get('commission')}%\n"
        f"Faixa de preço (somente se preenchida): R$ {product.get('price_min')} a R$ {product.get('price_max')}\n"
        f"Link de afiliado: {link}\n\n"
        "Regras obrigatórias:\n"
        "- Inclua o link de afiliado inteiro em cada versão; o link ocupa caracteres.\n"
        "- Não invente benefícios, avaliações, preço promocional, estoque ou desconto.\n"
        "- Threads: direto e até uma hashtag. X: conciso, link conta 23 caracteres.\n"
        "- Instagram: legenda visual. Facebook: explicação e CTA naturais.\n"
        "- TikTok: legenda orientada a vídeo e ao contexto da plataforma.\n"
        "- Respeite também os limites individuais de hashtags, links e menções.\n"
        "- Não explique o que fez. Responda SOMENTE com objeto JSON válido, "
        f"sem markdown, no formato: {{{shape}}}"
    )


def _shorten_prompt(variants: list[dict], texts: dict[str, str], issues: dict[str, list[str]]) -> str:
    parts = [
        f'{_limit_line(v)}\nProblemas: {"; ".join(issues[v["key"]])}\nTexto atual:\n{texts[v["key"]]}'
        for v in variants
    ]
    shape = ", ".join(f'"{v["key"]}": "texto"' for v in variants)
    return (
        "Os textos de post abaixo passaram do limite. Reescreva cada um MAIS CURTO, "
        "mantendo o produto, o tom e o link de afiliado intactos:\n\n"
        + "\n\n".join(parts)
        + f"\n\nResponda SOMENTE com um objeto JSON válido, sem markdown, no formato: {{{shape}}}"
    )


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_variants(raw: str, keys: list[str]) -> dict[str, str] | None:
    """Textos por chave do JSON da IA; None se não veio um JSON com todas."""
    cleaned = _FENCE_RE.sub("", raw.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    try:
        data = json.loads(cleaned[start:end + 1]) if start >= 0 else None
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    out = {k: str(data[k]).strip() for k in keys if isinstance(data.get(k), str) and data[k].strip()}
    return out if len(out) == len(keys) else None


def _ask(complete, prompt: str, keys: list[str]) -> dict[str, str]:
    from apis.llm import LLMError

    raw = complete(prompt, VARIANTS_MAX_TOKENS)
    parsed = parse_variants(raw, keys)
    if parsed is None and len(keys) == 1:
        parsed = {keys[0]: raw.strip()}  # modelo respondeu texto puro: serve pra 1 variante
    if parsed is None:
        raise LLMError("bad_response", "A IA não devolveu os textos no formato esperado. Tente novamente.")
    return parsed


def _keep_first_matches(text: str, pattern: re.Pattern, max_count: int | None) -> str:
    """Remove tags/menções excedentes; não altera as demais palavras."""
    if max_count is None:
        return text
    seen = 0

    def replace(match: re.Match) -> str:
        nonlocal seen
        seen += 1
        return match.group() if seen <= max_count else ""

    return pattern.sub(replace, text)


def _repair_variant(variant: dict, text: str, product: dict) -> str:
    """Fallback factual: não parte URL, preserva link e limita caracteres.

    Conserva o começo da descrição da IA quando possível; a UI informa a
    adaptação para revisão, sem publicar automaticamente.
    """
    from apis.llm import LLMError

    rules = [NETWORK_RULES[n] for n in variant["networks"]]
    link = (product.get("commission_link") or product.get("original_link") or "").strip()
    link = link if _URL_RE.fullmatch(link) else ""
    body = _URL_RE.sub("", text).strip() if link else text.strip()
    for rule_key, pattern in (("max_hashtags", _HASHTAG_RE), ("max_mentions", _MENTION_RE)):
        caps = [r[rule_key] for r in rules if rule_key in r]
        body = _keep_first_matches(body, pattern, min(caps) if caps else None)
    link_caps = [r["max_links"] for r in rules if "max_links" in r]
    if link and link_caps and min(link_caps) < 1:
        raise LLMError("bad_response", "O link do produto não cabe nas regras desta rede.")

    body = re.sub(r"[ \t]{2,}", " ", body)
    body = re.sub(r" *\n *", "\n", body).strip(" \n,;:-")
    suffix = f"\n{link}" if link else ""

    def compose(prefix: str) -> str:
        return (prefix.rstrip(" \n,;:-") + suffix).strip()

    candidate = compose(body)
    if candidate and not variant_issues(variant, candidate):
        return candidate

    # Busca binária: cada candidato usa o contador real (X ponderado, TikTok
    # UTF-16). O link permanece completo e também conta no orçamento.
    lo, hi = 0, len(body)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if variant_issues(variant, compose(body[:mid])):
            hi = mid - 1
        else:
            lo = mid

    prefix = body[:lo].rstrip()
    if lo < len(body):
        boundary = max(prefix.rfind("\n"), prefix.rfind(". "), prefix.rfind("! "), prefix.rfind("? "))
        if boundary >= max(35, len(prefix) // 2):
            prefix = prefix[:boundary + (1 if prefix[boundary] in ".!?" else 0)]
        elif " " in prefix:
            prefix = prefix.rsplit(" ", 1)[0]
    candidate = compose(prefix)
    if prefix.strip() and not variant_issues(variant, candidate):
        return candidate

    # Não inventa características; nome e link vêm do catálogo do dono.
    name = str(product.get("name") or "Produto Shopee").strip()
    for size in range(len(name), -1, -1):
        short = compose(f"Confira {name[:size].rstrip()}")
        if not variant_issues(variant, short):
            return short
    raise LLMError("bad_response", "Não foi possível gerar uma descrição válida para a rede.")


def generate_variants(product: dict, persona: str, networks: list[str], complete) -> list[dict]:
    """Uma solicitação de IA para todas as redes, com reparo validado.

    Refaz uma vez apenas variantes inválidas. Se a IA persistir, adapta
    conservadoramente e sinaliza. Nunca retorna descrição fora da regra.
    """
    variants = plan_variants(networks)
    keys = [v["key"] for v in variants]
    texts = _ask(complete, build_prompt(product, persona, variants), keys)
    issues = {v["key"]: variant_issues(v, texts[v["key"]]) for v in variants}
    over = [v for v in variants if issues[v["key"]]]

    if over:
        retry = _ask(complete, _shorten_prompt(over, texts, issues), [v["key"] for v in over])
        for v in over:
            texts[v["key"]] = retry[v["key"]]
            issues[v["key"]] = variant_issues(v, retry[v["key"]])

    adjusted: set[str] = set()
    link = (product.get("commission_link") or product.get("original_link") or "").strip()
    for v in variants:
        key = v["key"]
        if issues[key] or (v["networks"] and link and _URL_RE.fullmatch(link) and link not in texts[key]):
            repaired = _repair_variant(v, texts[key], product)
            adjusted.add(key)
            texts[key] = repaired
            issues[key] = variant_issues(v, repaired)
        if issues[key]:
            from apis.llm import LLMError
            raise LLMError("bad_response", "A IA não conseguiu gerar um texto válido. Tente novamente.")

    return [
        {**v, "text": texts[v["key"]], "over_limit": False, "issues": [],
         "adjusted": v["key"] in adjusted}
        for v in variants
    ]

# A personalização de produtos reaproveita a mesma IA/persona do compositor,
# mas não pode incluir links ou alterar os dados comerciais do produto.
_PRODUCT_DESCRIPTION_URL_RE = re.compile(
    r"(?i)(?:https?://|www\.|(?:s\.)?shopee\.(?:com\.br|com)|bit\.ly|t\.co)\S*"
)


def generate_short_product_description(product: dict, persona: str, complete) -> str:
    """Copy de produto sem URL, limitada ao teto ponderado de 280 do X.

    Reutiliza o gerador do post e os tons do provedor; nunca persiste dados
    nem altera comissão/links. A pessoa revisa o texto antes de salvar.
    """
    from apis.llm import LLMError, PERSONA_TONES
    from .network_limits import text_length

    name = str(product.get("name") or "").strip()
    if not name:
        raise LLMError("bad_response", "Produto sem nome para descrever.")
    tone = PERSONA_TONES.get(persona, PERSONA_TONES["casual"])
    prompt = (
        "Escreva UMA descrição curta de produto em português do Brasil, pronta "
        "para ser guardada no catálogo do usuário e reutilizada em redes sociais.\n"
        f"Produto: {name[:240]}\nTom: {tone}\n"
        "Máximo de 220 caracteres de texto (incluindo emojis), idealmente até 160.\n"
        "Descreva o produto de forma natural e verdadeira, sem inventar funções, "
        "preço, desconto, avaliações, urgência ou garantias. "
        "NÃO inclua links, URLs, @menções, hashtags, links de afiliados nem "
        "chamada para clicar. Entregue SOMENTE a descrição, sem aspas ou markdown."
    )
    raw = complete(prompt, 350)
    text = _PRODUCT_DESCRIPTION_URL_RE.sub("", raw.strip())
    text = re.sub(r"(?i)^\s*(?:descrição|legenda)\s*:\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip().strip(chr(34) + chr(39) + chr(96)).strip()
    if not text:
        raise LLMError("bad_response", "A IA não produziu uma descrição válida. Tente novamente.")

    # X pondera emoji com dois caracteres. Corte por palavra quando necessário,
    # sem partir pares unicode, e valide com o mesmo schema do PUT de produto.
    truncated = text_length(NETWORK_RULES["x"], text) > 280
    while text and text_length(NETWORK_RULES["x"], text) > 280:
        text = text[:-1]
    text = text.rstrip(" ,;:-")
    if not text:
        raise LLMError("bad_response", "A IA não produziu uma descrição válida. Tente novamente.")
    if truncated and " " in text:
        text = text.rsplit(" ", 1)[0].rstrip(" ,;:-")

    from .routers.products import ProductUpdate
    try:
        ProductUpdate.model_validate({"description": text})
    except ValueError:
        raise LLMError("bad_response", "A IA incluiu um link ou texto inválido. Tente novamente.") from None
    return text


# Limite próprio do aplicativo. Não equivale a uma cota anti-spam oficial:
# cada provedor ainda aplica limites de API e políticas de automação.
MAX_THREAD_PARTS = 10


def _reply_networks(networks: list[str]) -> list[str]:
    """Only publishers that actually send chained replies constrain replies."""
    selected = [n for n in dict.fromkeys(networks)
                if n in NETWORK_RULES and NETWORK_RULES[n]["thread_parts"]]
    return selected or ["threads"]


def _parse_reply_parts(raw: str, expected: int) -> list[str] | None:
    cleaned = _FENCE_RE.sub("", raw.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    try:
        payload = json.loads(cleaned[start:end + 1]) if start >= 0 else None
    except ValueError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("parts"), list):
        return None
    parts = payload["parts"]
    if len(parts) != expected or any(not isinstance(p, str) or not p.strip() for p in parts):
        return None
    return [part.strip() for part in parts]


def _reply_issues(parts: list[str], networks: list[str]) -> list[str]:
    problems = []
    for i, part in enumerate(parts, start=1):
        for network in networks:
            # No media on follow-up posts: validate only the text.
            for issue in validate_post(network, [part], [], 0, False):
                if issue["level"] == "error":
                    problems.append(f"Parte {i}, {issue['message']}")
    return problems


def generate_thread_replies(
    product: dict,
    persona: str,
    networks: list[str],
    previous_parts: list[str],
    count: int,
    complete,
) -> list[str]:
    """Generate exactly the missing continuation parts in one LLM request.

    The caller supplies coherent preceding text. The function never publishes,
    silently truncates, or rewrites existing user-entered parts. Retries once
    if the provider returns invalid JSON or platform-incompatible text.
    """
    from apis.llm import LLMError, PERSONA_TONES

    if count < 0 or count > MAX_THREAD_PARTS - len(previous_parts):
        raise ValueError("Quantidade de partes fora do limite do aplicativo")
    if count == 0:
        return []
    allowed_networks = _reply_networks(networks)
    max_chars = min(NETWORK_RULES[n]["max_chars"] for n in allowed_networks)
    tone = PERSONA_TONES.get(persona, PERSONA_TONES["casual"])
    # Bound context cost; don't send arbitrarily long manually entered content.
    context = "\n\n".join(
        f"Parte {index + 1}: {part[:1200]}"
        for index, part in enumerate(previous_parts[-MAX_THREAD_PARTS:])
    )
    link = product.get("commission_link") or product.get("original_link") or ""
    prompt = (
        "Você escreve uma sequência de respostas para uma publicação comercial "
        "de afiliados Shopee, em português do Brasil.\n"
        f"Produto: {product.get('name', '')}\n"
        f"Tom: {tone}\n"
        f"Link presente no post inicial: {link}\n"
        f"Trechos já escritos (não os repita nem reescreva):\n{context}\n\n"
        f"Gere EXATAMENTE {count} nova(s) parte(s) consecutiva(s) para continuar "
        f"esta thread, cada uma com no máximo {max_chars} caracteres. "
        "O limite inclui espaços, emojis, hashtags e links.\n"
        "Uma ideia complementar por parte; progressão narrativa coerente; "
        "não invente preços, garantias, avaliações ou escassez; "
        "não repita link, CTA nem hashtags em todas as respostas. "
        "No Threads, no máximo uma hashtag por parte. "
        "O texto deve estar pronto para publicar, sem títulos como 'Parte 2'.\n"
        "Responda APENAS com JSON válido: "
        '{"parts": ["resposta 1", "resposta 2"]}. '
        "O array deve ter exatamente a quantidade solicitada."
    )

    def ask(message: str) -> list[str] | None:
        raw = complete(message, min(4096, max(1200, count * 350 + 500)))
        return _parse_reply_parts(raw, count)

    parts = ask(prompt)
    issues = _reply_issues(parts, allowed_networks) if parts else ["JSON ou quantidade inválida"]
    if issues:
        correction = (
            prompt + "\n\nA resposta anterior estava inválida. "
            "Refaça TODAS as partes, corrigindo estes problemas:\n"
            + "\n".join(issues[:20])
            + "\nMantenha um array JSON com a quantidade exata."
        )
        parts = ask(correction)
        issues = _reply_issues(parts, allowed_networks) if parts else ["JSON ou quantidade inválida"]
    if issues or parts is None:
        raise LLMError(
            "bad_response",
            "A IA não conseguiu gerar as respostas dentro dos limites. Tente novamente.",
        )
    return parts
