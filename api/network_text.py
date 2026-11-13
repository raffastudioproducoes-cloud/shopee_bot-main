"""Defesa em profundidade: texto por rede que vazou como JSON vira texto limpo.

A IA devolve `{"threads": "texto", ...}`. Se esse objeto chegar inteiro a um
post (resposta com quebra de linha crua, cliente antigo, dado já gravado),
nada deve publicar nem exibir o JSON: escolhe o texto da rede e, sem ela,
o primeiro texto do mapa.
"""

import json

from .network_limits import NETWORK_RULES


def _variant_key(key) -> bool:
    # Chaves de rede ou a faixa genérica legada ("2200").
    return isinstance(key, str) and (key in NETWORK_RULES or key.isdigit())


def unwrap_network_text(text, network: str | None = None):
    """Texto da rede se `text` for um mapa rede->texto; senão, `text` intacto."""
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return text
    try:
        # strict=False: modelos costumam pôr quebras de linha cruas nas strings.
        data = json.loads(stripped, strict=False)
    except ValueError:
        return text
    if (not isinstance(data, dict) or not data
            or not all(_variant_key(k) for k in data)
            or not all(isinstance(v, str) and v.strip() for v in data.values())):
        return text
    value = data[network] if network in data else next(iter(data.values()))
    return value.strip()
