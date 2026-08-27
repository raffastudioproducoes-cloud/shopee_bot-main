import os

import requests


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-1.5-flash:generateContent"
)

# Tom de escrita por persona. Ajusta a voz do copy gerado.
PERSONA_TONES = {
    "casual": "tom descontraído e conversado, como se falasse com um amigo",
    "profissional": "tom profissional e confiável, focado em benefícios e credibilidade",
    "divertido": "tom divertido, engraçado e com emojis",
    "persuasivo": (
        "tom altamente persuasivo, com gatilhos de urgência e prova social"
    ),
}


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


def _call_gemini(prompt, api_key):
    if not api_key:
        raise Exception("GEMINI_API_KEY não configurada no servidor.")

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 600,
        },
    }

    try:
        res = requests.post(
            GEMINI_URL, headers=headers, json=payload, timeout=60
        )
    except requests.exceptions.RequestException as e:
        raise Exception(f"Falha de conexão com a API Gemini: {e}")

    if res.status_code != 200:
        raise Exception(
            f"Erro na API Gemini (status {res.status_code}): "
            f"{res.text[:300]}"
        )

    data = res.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        raise Exception("Resposta inesperada da API Gemini.")


def generate_product_copy(product, persona="casual"):
    """Gera o texto de um post de afiliado Shopee a partir de um produto.

    Lê a chave de API de os.environ (GEMINI_API_KEY) e o provedor de
    LLM_PROVIDER (padrão 'gemini'). Retorna apenas o texto do post ou levanta
    Exception clara em caso de falha.
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    api_key = os.environ.get("GEMINI_API_KEY")
    prompt = _build_prompt(product, persona)

    if provider == "gemini":
        return _call_gemini(prompt, api_key)

    # Ponto de extensão: openai/ollama poderiam ser adicionados aqui.
    raise Exception(f"Provedor de LLM '{provider}' não suportado.")
