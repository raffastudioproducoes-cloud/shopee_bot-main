"""
Sanitização de dado sensível antes de gravar ou servir log de auditoria.

Duas defesas, nenhuma sozinha é suficiente:

1. Por NOME de chave (case-insensitive, cobrindo snake_case/camelCase) —
   pega o caso comum (`password`, `access_token`, header `Authorization`).
2. Por PADRÃO DE VALOR — pega o caso em que a chave não bate com a lista
   (ex: token colado dentro de uma mensagem de erro em texto livre) ou um
   nome de chave que ainda não previmos.

Aplicada em dois pontos (defesa em profundidade — ver requisito do dono do
projeto): antes de INSERIR o log de passo de negócio (api/audit_log.py) e de
novo ao SERVIR pela API de leitura (api/routers/logs.py), caso algo escape
do primeiro ponto (ex: um campo novo adicionado depois sem passar por lá).
"""

import re

_MASK = "***REDACTED***"

# Nomes de chave sensíveis. Comparação normaliza pra snake_case minúsculo
# antes de checar (ver _normalize_key), então uma entrada aqui cobre
# "access_token", "accessToken", "Access-Token" etc de uma vez.
_SENSITIVE_KEYS = {
    "password",
    "senha",
    "secret",
    "client_secret",
    "token",
    "access_token",
    "refresh_token",
    "user_access_token",
    "user_refresh_token",
    "id_token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "set_cookie",
    "code_verifier",
    "code_challenge",
    "private_key",
}

# Padrões de VALOR que parecem segredo mesmo sob uma chave desconhecida:
# JWT (header.payload.signature, cada parte base64url) e "Bearer <token>".
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE)

# Chave sensível dentro de TEXTO LIVRE (ex: payload serializado colado
# numa mensagem de erro) — casa `"password": "xxx"`, `password=xxx`,
# `'token': 'xxx'` etc e mascara só o valor, mantendo a chave visível
# (ajuda debug: sabe QUE campo era segredo, sem expor o segredo).
_KEY_VALUE_RE = re.compile(
    r"""(?i)(["']?(?:password|senha|secret|token|access_token|refresh_token|
    user_access_token|user_refresh_token|client_secret|api_key|apikey)["']?
    \s*[:=]\s*)(["']?)([^"',}\s]+)\2""",
    re.VERBOSE,
)


def _normalize_key(key: str) -> str:
    """"accessToken" / "Access-Token" / "ACCESS_TOKEN" -> "access_token".

    Só insere `_` na fronteira minúscula->maiúscula (camelCase real,
    ex: "accessToken"). Uma string já toda maiúscula (ex: "API_KEY")
    não tem essa fronteira, então passa direto — inserir `_` antes de
    CADA letra maiúscula quebraria "ACCESS_TOKEN" em "a_c_c_e_s_s_...".
    """
    snake = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    snake = snake.replace("-", "_").replace(" ", "_")
    snake = re.sub(r"_+", "_", snake)
    return snake.lower()


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    return normalized in _SENSITIVE_KEYS or any(
        s in normalized for s in ("password", "secret", "token", "api_key")
    )


def _sanitize_string(value: str) -> str:
    value = _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{_MASK}{m.group(2)}", value)
    value = _JWT_RE.sub(_MASK, value)
    value = _BEARER_RE.sub(f"Bearer {_MASK}", value)
    return value


def sanitize_log_data(data, *, mask_value_patterns: bool = True):
    """Recebe dict ou string livre; devolve versão sem segredo em texto claro.

    dict: mascara valor de toda chave sensível (recursivo em dict/list
    aninhado) e ainda passa valores string restantes pelo detector de
    padrão. string: só passa pelo detector de padrão (não há "chave" pra
    checar). Qualquer outro tipo volta sem alteração.

    `mask_value_patterns=False` desliga só o detector de PADRÃO de valor
    (JWT solto, "Bearer x", `token=x` em texto livre) — mantém a máscara
    por NOME de chave. Uso: backup pessoal (`GET/POST /users/me/backup`
    e `/restore`) tem link/URL legítimo do próprio dono contendo
    `?token=` na query string (ex: link de afiliado), e o detector de
    padrão originalmente pensado pra log de erro/texto livre estragava
    esse dado — decisão: manter a defesa por chave (pega segredo de
    verdade tipo campo `password`/`access_token`), desligar só o scan
    de texto livre nesse fluxo específico.
    """
    if isinstance(data, str):
        return _sanitize_string(data) if mask_value_patterns else data

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if _is_sensitive_key(str(key)):
                result[key] = _MASK if value is not None else value
            else:
                result[key] = sanitize_log_data(value, mask_value_patterns=mask_value_patterns)
        return result

    if isinstance(data, list):
        return [sanitize_log_data(item, mask_value_patterns=mask_value_patterns) for item in data]

    return data
