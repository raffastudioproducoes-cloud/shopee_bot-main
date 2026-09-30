"""
Regras de negócio puras do módulo de perfis (multi-profile).

Sem I/O — só as regras que o router `api/routers/profiles.py` aplica em
torno das chamadas ao Supabase.
"""

PROFILE_LIMIT = 3
VALID_KINDS = ("principal", "secundario")
VALID_PLAN_TIERS = ("free", "plus", "premium")


def can_create_profile(existing_count: int) -> bool:
    return existing_count < PROFILE_LIMIT


def is_principal(profile: dict) -> bool:
    return profile.get("kind") == "principal"


def _demo() -> None:
    assert can_create_profile(0) is True
    assert can_create_profile(2) is True
    assert can_create_profile(3) is False
    assert is_principal({"kind": "principal"}) is True
    assert is_principal({"kind": "secundario"}) is False
    assert is_principal({}) is False


if __name__ == "__main__":
    _demo()
    print("ok")
