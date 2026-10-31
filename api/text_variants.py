"""
Conjunto MÍNIMO de textos que atende todas as redes marcadas num post.

Cada rede recebe o texto mais longo que ela aceita: redes com o mesmo limite
efetivo compartilham um texto; cada faixa de limite diferente ganha o seu
(ex.: Facebook+Instagram -> um texto de até 2.200; X -> um de até 280).

Limite efetivo = max_chars da rede (api/network_limits.py) limitado por
PRACTICAL_MAX_CHARS: o Facebook aceita 63 mil, mas copy de venda não precisa
disso. A contagem real (X: link = 23, emoji = 2; TikTok: UTF-16) e os
limites de hashtag/link/@menção são cobrados por `validate_post` em cada
rede do grupo, a mesma regra que o POST /posts aplica.
"""

import json
import re

from .network_limits import NETWORK_RULES, validate_post

# Teto recomendável de uma copy de vendas (mesmo do Instagram/TikTok).
PRACTICAL_MAX_CHARS = 2200
# Variantes em JSON + raciocínio dos modelos que "pensam" (ver apis/llm.py).
VARIANTS_MAX_TOKENS = 4096

_TEXT_LIMIT_KEYS = (("max_hashtags", "hashtag(s)"), ("max_links", "link(s)"), ("max_mentions", "@menções"))


def effective_limit(network: str) -> int:
    return min(NETWORK_RULES[network]["max_chars"], PRACTICAL_MAX_CHARS)


def plan_variants(networks: list[str]) -> list[dict]:
    """Grupos por limite efetivo, do mais longo pro mais curto.

    `[{key, max_chars, networks}]`; sem rede = um texto de até
    PRACTICAL_MAX_CHARS. Ordem das redes segue NETWORK_RULES."""
    chosen = [n for n in NETWORK_RULES if n in set(networks)]
    if not chosen:
        return [{"key": str(PRACTICAL_MAX_CHARS), "max_chars": PRACTICAL_MAX_CHARS, "networks": []}]
    by_limit: dict[int, list[str]] = {}
    for n in chosen:
        by_limit.setdefault(effective_limit(n), []).append(n)
    return [
        {"key": str(limit), "max_chars": limit, "networks": by_limit[limit]}
        for limit in sorted(by_limit, reverse=True)
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
        "Você é um copywriter de afiliados da Shopee. Escreva o post para divulgar o "
        f"produto abaixo, em português do Brasil, com {tone}.\n"
        f"Gere {len(variants)} versão(ões) do MESMO post (mesmo produto, mesma persona e "
        "tom), uma para cada limite de tamanho. Use o espaço de cada uma, sem passar:\n"
        + "\n".join(_limit_line(v) for v in variants) + "\n\n"
        f"Produto: {product.get('name', '')}\n"
        f"Comissão: {product.get('commission')}%\n"
        f"Faixa de preço: R$ {product.get('price_min')} a R$ {product.get('price_max')}\n"
        f"Link de afiliado: {link}\n\n"
        "Regras:\n"
        "- Inclua o link de afiliado em cada versão; ele e as hashtags contam no limite.\n"
        "- Texto pronto para publicar, com quebras de linha naturais.\n"
        "- Não explique o que fez e não repita estas instruções.\n"
        "- Responda SOMENTE com um objeto JSON válido, sem markdown, no formato: "
        f"{{{shape}}}"
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


def generate_variants(product: dict, persona: str, networks: list[str], complete) -> list[dict]:
    """Uma chamada pra todas as variantes; refaz UMA vez só as que passaram
    do limite; se ainda passar, devolve com `over_limit=True` (sem truncar).

    `complete(prompt, max_tokens) -> str` (apis.llm.complete já com chave)."""
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

    return [
        {**v, "text": texts[v["key"]], "over_limit": bool(issues[v["key"]]), "issues": issues[v["key"]]}
        for v in variants
    ]


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
