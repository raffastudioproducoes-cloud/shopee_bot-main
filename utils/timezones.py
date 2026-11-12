"""Fuso horario IANA: validacao unica para API, Flask e scheduler."""

from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

DEFAULT_TIMEZONE = "America/Sao_Paulo"
MAX_TIMEZONE_LENGTH = 64


@lru_cache(maxsize=1)
def _known_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def normalize_timezone(value) -> str:
    """Devolve o nome IANA exato ou levanta ValueError (sem eco do valor)."""
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_TIMEZONE_LENGTH
        or value not in _known_timezones()
    ):
        raise ValueError("Fuso horario invalido")
    return value


def timezone_or_default(value) -> str:
    """Linhas antigas/sem fuso e nomes invalidos ficam no fuso historico."""
    try:
        return normalize_timezone(value)
    except ValueError:
        return DEFAULT_TIMEZONE


def zone(value) -> ZoneInfo:
    return ZoneInfo(timezone_or_default(value))
