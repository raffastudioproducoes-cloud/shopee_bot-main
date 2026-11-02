"""Contexto estritamente local à execução de uma ocorrência já reivindicada.

Nunca altera posts, agendas ou mídias persistentes. Uma tentativa sem revisão
continua usando o conteúdo original.
"""
from contextvars import ContextVar

_active_snapshot = ContextVar("orbital_post_content_snapshot", default=None)


def bind(snapshot):
    return _active_snapshot.set(snapshot)


def reset(token):
    _active_snapshot.reset(token)


def get():
    return _active_snapshot.get()


def apply_to_parts(parts, snapshot):
    """Projeção apenas em memória. Falha fechada se snapshot estiver inválido."""
    if snapshot is None:
        return parts
    if (
        not parts or not isinstance(snapshot, dict)
        or not isinstance(snapshot.get("texts"), list)
        or not snapshot["texts"]
        or not all(isinstance(text, str) and text.strip() for text in snapshot["texts"])
        or not isinstance(snapshot.get("medias"), list)
        or not isinstance(snapshot.get("product_ids"), list)
    ):
        raise ValueError("Snapshot de publicação inválido; envio bloqueado")

    result = []
    for idx, text in enumerate(snapshot["texts"]):
        row = dict(parts[idx] if idx < len(parts) else parts[-1])
        row["text"] = text
        row["depth"] = idx
        row["product_ids"] = list(snapshot["product_ids"]) if idx == 0 else []
        row["medias"] = list(snapshot["medias"]) if idx == 0 else []
        result.append(row)
    return result
