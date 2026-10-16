"""Lease curto e atômico para uma execução de publicação por scheduler."""

from shopee_bot.database import query_db


def try_claim(scheduler_id: str, lease_seconds: int) -> str | None:
    result = query_db(
        """
        INSERT INTO publication_claims (scheduler_id, claim_token, claimed_at)
        VALUES (%s, gen_random_uuid(), now())
        ON CONFLICT (scheduler_id) DO UPDATE
        SET claim_token = EXCLUDED.claim_token,
            claimed_at = EXCLUDED.claimed_at
        WHERE publication_claims.claimed_at < now() - make_interval(secs => %s)
        RETURNING claim_token
        """,
        (scheduler_id, lease_seconds),
        one=True,
    )
    return str(result["claim_token"]) if result else None


def release(scheduler_id: str, claim_token: str) -> None:
    query_db(
        """
        DELETE FROM publication_claims
        WHERE scheduler_id = %s AND claim_token = %s
        RETURNING scheduler_id
        """,
        (scheduler_id, claim_token),
        one=True,
    )
