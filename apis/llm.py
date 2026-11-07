"""Copywriter IA: chamadas dos provedores com credencial fornecida SOMENTE
pelo backend (api/routers/platform_ai.py). Jamais expor a chave no cliente.

Endpoints e modelos padrão conferidos nas docs oficiais em 2026-10-07:
- Gemini: POST generativelanguage.googleapis.com/v1beta/models/{model}:generateContent,
  header x-goog-api-key (ai.google.dev/api/generate-content). Padrão
  gemini-3.5-flash-lite (estável, o mais barato da linha 3.5).
- OpenAI: POST api.openai.com/v1/responses, Authorization: Bearer
  (developers.openai.com/api/reference). Padrão gpt-6-luna (o mais barato).
- Anthropic: POST api.anthropic.com/v1/messages, x-api-key +
  anthropic-version: 2023-06-01 (platform.claude.com/docs). Padrão
  claude-sonnet-5-5 (Haiku 4.5 é mais barato mas tem aposentadoria prevista
  a partir de 15/10/2026; dá pra trocar o modelo por credencial).

Nunca inclui a chave nem o corpo cru da resposta do provedor nas mensagens de
erro (o corpo pode ecoar dados da requisição).
"""

import re

import httpx

PROVIDERS = ("gemini", "openai", "anthropic")

DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash-lite",
    "openai": "gpt-6-luna",
    "anthropic": "claude-sonnet-5-5",
}

# Sobra pra modelos que "pensam" antes de responder (Gemini 3.x, gpt-6-*,
# Claude 5.x): os tokens de raciocínio contam no mesmo limite de saída.
MAX_OUTPUT_TOKENS = 2048
TIMEOUT_SECONDS = 60

# id de modelo vira parte da URL do Gemini: só caracteres seguros.
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")

# Tom de escrita por persona. Ajusta a voz do copy gerado.
PERSONA_TONES = {
    "casual": "tom descontraído e conversado, como se falasse com um amigo",
    "profissional": "tom profissional e confiável, focado em benefícios e credibilidade",
    "divertido": "tom divertido, engraçado e com emojis",
    "persuasivo": (
        "tom altamente persuasivo, com gatilhos de urgência e prova social"
    ),
}


class LLMError(Exception):
    """Falha ao chamar o provedor. `kind`: invalid_key | quota | model |
    network | bad_response | provider. Mensagem segura pra mostrar ao usuário."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


def valid_model(model: str | None) -> bool:
    return bool(model and _MODEL_RE.match(model))


def _build_prompt(product, persona):
    name = product.get("name", "")
    commission = product.get("commission")
    price_min = product.get("price_min")
    price_max = product.get("price_max")
    link = product.get("commission_link") or product.get("original_link") or ""
    tone = PERSONA_TONES.get(persona, PERSONA_TONES["casual"])

    return (
        "Você é um copywriter de afiliados da Shopee. Escreva um post persuasivo "
        f"para divulgar o produto abaixo, em português do Brasil, com {tone}.\n\n"
        f"Produto: {name}\n"
        f"Comissão: {commission}%\n"
        f"Faixa de preço: R$ {price_min} a R$ {price_max}\n"
        f"Link de afiliado: {link}\n\n"
        "Regras:\n"
        "- Inclua o link de afiliado no texto.\n"
        "- Texto pronto para publicar (Instagram/Threads/Facebook), com quebras "
        "de linha naturais.\n"
        "- Não use aspas no início/fim, não explique o que fez e não repita "
        "estas instruções.\n"
        "- Retorne apenas o texto do post."
    )


def _request(provider: str, api_key: str, model: str, prompt: str, max_tokens: int):
    """(url, headers, json) da chamada de cada provedor."""
    if provider == "gemini":
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            {"x-goog-api-key": api_key, "Content-Type": "application/json"},
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
        )
    if provider == "openai":
        return (
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            {"model": model, "input": prompt, "max_output_tokens": max_tokens},
        )
    return (
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
    )


def _extract_text(provider: str, data: dict) -> str:
    if provider == "gemini":
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    if provider == "openai":
        return "".join(
            c.get("text", "")
            for item in data.get("output", []) if item.get("type") == "message"
            for c in item.get("content", []) if c.get("type") == "output_text"
        )
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _error_for_status(status: int, body: str) -> LLMError:
    low = body.lower()
    if status in (401, 403) or "api_key_invalid" in low or "api key not valid" in low:
        return LLMError("invalid_key", "Serviço de IA indisponível por configuração. Contate o suporte.")
    if status == 429 or "insufficient_quota" in low or "resource_exhausted" in low:
        return LLMError("quota", "Sem cota ou limite de uso atingido no provedor de IA. Verifique seu plano/créditos.")
    if status == 404 or (status == 400 and "model" in low):
        return LLMError(
            "model", "Modelo de IA indisponível. Contate o suporte."
        )
    return LLMError("provider", f"O provedor de IA recusou a requisição (status {status}). Tente novamente.")


def complete(provider: str, api_key: str, model: str | None, prompt: str,
             max_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    if provider not in PROVIDERS:
        raise LLMError("provider", "Provedor de IA não suportado.")
    if not api_key:
        raise LLMError("invalid_key", "Serviço de IA indisponível. Contate o suporte.")
    model = model or DEFAULT_MODELS[provider]
    if not valid_model(model):
        raise LLMError("model", "Nome de modelo de IA inválido.")

    url, headers, payload = _request(provider, api_key, model, prompt, max_tokens)
    try:
        res = httpx.post(url, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError:
        raise LLMError("network", "Falha de rede ao falar com o provedor de IA. Tente novamente.") from None

    if res.status_code != 200:
        raise _error_for_status(res.status_code, res.text)

    try:
        text = _extract_text(provider, res.json()).strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise LLMError("bad_response", "Resposta inesperada do provedor de IA.") from None
    if not text:
        raise LLMError("bad_response", "O provedor de IA não devolveu texto.")
    return text


def generate_product_copy(product, persona, provider, api_key, model=None):
    """Texto de afiliado Shopee a partir de um produto; chave só no servidor."""
    return complete(provider, api_key, model, _build_prompt(product, persona))


def check_key(provider, api_key, model=None):
    """Chamada mínima pra validar chave + modelo ("Testar conexão")."""
    complete(provider, api_key, model, "Responda apenas: ok", max_tokens=256)
