"""Operacoes atomicas da fila duravel de publicacao."""

from shopee_bot.database import query_db
from api.utils.log_sanitizer import sanitize_log_data


TERMINAL_STATUSES = frozenset({"succeeded", "failed", "unknown"})


def recoverable(lease_seconds, limit=100):
    """Somente itens que ainda nao iniciaram chamada externa podem ser retomados."""
    query = """
        SELECT id, scheduler_id
        FROM publish_jobs
        WHERE status = 'pending'
        ORDER BY created_at
        LIMIT %s
    """
    return query_db(query, (limit,))


MAX_PREFLIGHT_ATTEMPTS = 5


def expire_running(lease_seconds):
    """Retoma apenas envios sem chamada externa; preserva incerteza apos a API."""
    query = """
        UPDATE publish_jobs
        SET status = CASE
                WHEN external_started_at IS NOT NULL THEN 'unknown'
                WHEN attempt >= %s THEN 'failed'
                ELSE 'pending'
            END,
            last_error = CASE
                WHEN external_started_at IS NOT NULL
                    THEN 'Lease expirado apos inicio de chamada externa; requer conciliacao'
                WHEN attempt >= %s
                    THEN 'Preparacao interrompida repetidamente; requer intervencao'
                ELSE 'Preparacao interrompida antes de chamada externa; retomada segura'
            END,
            finished_at = CASE
                WHEN external_started_at IS NULL AND attempt < %s THEN NULL
                ELSE now()
            END,
            claim_token = NULL, locked_by = NULL, locked_at = NULL
        WHERE status = 'running'
          AND locked_at < now() - make_interval(secs => %s)
        RETURNING id, status
    """
    return query_db(query, (
        MAX_PREFLIGHT_ATTEMPTS, MAX_PREFLIGHT_ATTEMPTS,
        MAX_PREFLIGHT_ATTEMPTS, lease_seconds,
    ))


def enqueue(*, scheduler_id, post_id, user_id, profile_id, network, idempotency_key):
    """Cria uma ocorrencia ou devolve a mesma ocorrencia ja persistida."""
    query = """
        INSERT INTO publish_jobs (
            scheduler_id, post_id, user_id, profile_id, network, idempotency_key
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO UPDATE
            SET idempotency_key = EXCLUDED.idempotency_key
        RETURNING id, status
    """
    return query_db(
        query,
        (scheduler_id, post_id, user_id, profile_id, network, idempotency_key),
        one=True,
    )


def claim(publish_job_id, worker_id, lease_seconds):
    """Um unico worker pode adquirir item que ainda nao foi iniciado."""
    query = """
        WITH candidate AS (
            SELECT id
            FROM publish_jobs
            WHERE id = %s
              AND status = 'pending'
            FOR UPDATE SKIP LOCKED
        )
        UPDATE publish_jobs AS job
        SET status = 'running',
            attempt = job.attempt + 1,
            claim_token = gen_random_uuid(),
            locked_by = %s,
            locked_at = now(),
            started_at = COALESCE(job.started_at, now())
        FROM candidate
        WHERE job.id = candidate.id
        RETURNING job.id, job.claim_token
    """
    return query_db(query, (publish_job_id, worker_id), one=True)


def finish(publish_job_id, claim_token, status, *, external_id=None, error=None):
    if status not in TERMINAL_STATUSES:
        raise ValueError("status terminal invalido")
    query = """
        UPDATE publish_jobs
        SET status = %s,
            external_id = %s,
            last_error = %s,
            finished_at = now(),
            claim_token = NULL,
            locked_by = NULL,
            locked_at = NULL
        WHERE id = %s AND claim_token = %s
        RETURNING id, status
    """
    return query_db(
        query,
        (status, external_id, sanitize_log_data(error) if error else None, publish_job_id, claim_token),
        one=True,
    )


def mark_external_started(publish_job_id, claim_token):
    """Barreira duravel ANTES da primeira operacao mutavel no provedor."""
    return query_db(
        """
        UPDATE publish_jobs
        SET external_started_at = COALESCE(external_started_at, now())
        WHERE id = %s AND claim_token = %s AND status = 'running'
        RETURNING id
        """,
        (publish_job_id, claim_token),
        one=True,
    )


def requeue_if_safe(publish_job_id, claim_token):
    """Desfaz claim apenas enquanto nenhuma chamada externa foi iniciada."""
    return query_db(
        """
        UPDATE publish_jobs
        SET status = 'pending', claim_token = NULL, locked_by = NULL,
            locked_at = NULL, finished_at = NULL,
            last_error = 'Encerramento antes da chamada externa; aguardando retomada'
        WHERE id = %s AND claim_token = %s AND status = 'running'
          AND external_started_at IS NULL
        RETURNING id
        """,
        (publish_job_id, claim_token),
        one=True,
    )
