"""Resultado explicito de um publicador para a fila duravel."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicationResult:
    status: str
    external_id: str | None = None
    error: str | None = None


def succeeded(external_id=None):
    return PublicationResult("succeeded", str(external_id) if external_id else None)


def failed(error):
    return PublicationResult("failed", error=str(error)[:500])


def unknown(error):
    return PublicationResult("unknown", error=str(error)[:500])


def external_id(value):
    if isinstance(value, dict):
        value = value.get("id") or value.get("post_id") or value.get("media_id")
    return str(value) if value is not None else None
