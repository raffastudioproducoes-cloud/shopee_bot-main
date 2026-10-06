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


def scope_owner(query, user_id, profile_id: str | None):
    """Filtra por dono (`user_id`) e, quando há perfil ativo, por `profile_id`.

    Sem perfil ativo (token antigo) mantém só o filtro por `user_id`
    (fallback já usado em products/lists)."""
    query = query.eq("user_id", user_id)
    return query.eq("profile_id", profile_id) if profile_id else query


def is_principal(profile: dict) -> bool:
    return profile.get("kind") == "principal"


def _demo() -> None:
    class _Q:
        def __init__(self):
            self.calls = []

        def eq(self, k, v):
            self.calls.append((k, v))
            return self

    assert scope_owner(_Q(), 1, None).calls == [("user_id", 1)]
    assert scope_owner(_Q(), 1, "p").calls == [("user_id", 1), ("profile_id", "p")]
    assert can_create_profile(0) is True
    assert can_create_profile(2) is True
    assert can_create_profile(3) is False
    assert is_principal({"kind": "principal"}) is True
    assert is_principal({"kind": "secundario"}) is False
    assert is_principal({}) is False


if __name__ == "__main__":
    _demo()
    print("ok")
