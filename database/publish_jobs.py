"""Operacoes atomicas da fila duravel de publicacao."""

from shopee_bot.database import query_db
from shopee_bot.database.scheduler_environment import current_environment
from shopee_bot.database.central_dispatch import central_dispatch_enabled, publication_scope_sql


def _execution_scope():
    if central_dispatch_enabled():
        return publication_scope_sql("schedule")
    return "schedule.environment = %s", (current_environment(),)
from api.utils.log_sanitizer import sanitize_log_data


TERMINAL_STATUSES = frozenset({"succeeded", "failed", "unknown"})


def recoverable(lease_seconds, limit=100):
    """Somente itens que ainda nao iniciaram chamada externa podem ser retomados."""
    scope, scope_args = _execution_scope()
    query = f"""
        SELECT job.id, job.scheduler_id
        FROM publish_jobs job
        JOIN schedulers schedule ON schedule.id = job.scheduler_id
          AND schedule.post_id = job.post_id
          AND schedule.user_id = job.user_id
          AND schedule.profile_id IS NOT DISTINCT FROM job.profile_id
        WHERE job.status = 'pending'
          AND ({scope})
        ORDER BY job.created_at
        LIMIT %s
    """
    return query_db(query, (*scope_args, limit))


MAX_PREFLIGHT_ATTEMPTS = 5


def expire_running(lease_seconds):
    """Retoma apenas envios sem chamada externa; preserva incerteza apos a API."""
    scope, scope_args = _execution_scope()
    query = f"""
        UPDATE publish_jobs
        SET status = CASE
                WHEN external_started_at IS NOT NULL
                     OR preflight_claim_token IS DISTINCT FROM claim_token
                    THEN 'unknown'
                WHEN attempt >= %s THEN 'failed'
                ELSE 'pending'
            END,
            last_error = CASE
                WHEN external_started_at IS NOT NULL
                    THEN 'Lease expirado apos inicio de chamada externa; requer conciliacao'
                WHEN preflight_claim_token IS DISTINCT FROM claim_token
                    THEN 'Lease de worker legado ou desconhecido; requer conciliacao'
                WHEN attempt >= %s
                    THEN 'Preparacao interrompida repetidamente; requer intervencao'
                ELSE 'Preparacao interrompida antes de chamada externa; retomada segura'
            END,
            finished_at = CASE
                WHEN external_started_at IS NULL
                     AND preflight_claim_token = claim_token
                     AND attempt < %s THEN NULL
                ELSE now()
            END,
            claim_token = NULL, locked_by = NULL, locked_at = NULL
        WHERE status = 'running'
          AND locked_at < now() - make_interval(secs => %s)
          AND EXISTS (
              SELECT 1 FROM schedulers schedule
              WHERE schedule.id = publish_jobs.scheduler_id
                AND schedule.post_id = publish_jobs.post_id
                AND schedule.user_id = publish_jobs.user_id
                AND schedule.profile_id IS NOT DISTINCT FROM publish_jobs.profile_id
                AND ({scope})
          )
        RETURNING id, status
    """
    return query_db(query, (
        MAX_PREFLIGHT_ATTEMPTS, MAX_PREFLIGHT_ATTEMPTS,
        MAX_PREFLIGHT_ATTEMPTS, lease_seconds, *scope_args,
    ))


def enqueue(*, scheduler_id, post_id, user_id, profile_id, network, idempotency_key):
    """Cria uma ocorrencia ou devolve a mesma ocorrencia ja persistida."""
    query = """
        INSERT INTO publish_jobs (
            scheduler_id, post_id, user_id, profile_id, network, idempotency_key
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO UPDATE
            SET idempotency_key = EXCLUDED.idempotency_key
        WHERE publish_jobs.scheduler_id = EXCLUDED.scheduler_id
          AND publish_jobs.post_id = EXCLUDED.post_id
          AND publish_jobs.user_id = EXCLUDED.user_id
          AND publish_jobs.profile_id IS NOT DISTINCT FROM EXCLUDED.profile_id
          AND publish_jobs.network = EXCLUDED.network
        RETURNING id, status
    """
    result = query_db(
        query,
        (scheduler_id, post_id, user_id, profile_id, network, idempotency_key),
        one=True,
    )
    if not result:
        raise RuntimeError("Conflito de identidade na fila de publicação")
    return result


def claim(publish_job_id, worker_id, lease_seconds):
    """Um unico worker pode adquirir item que ainda nao foi iniciado."""
    scope, scope_args = _execution_scope()
    query = f"""
        WITH candidate AS (
            SELECT job.id, gen_random_uuid() AS token
            FROM publish_jobs job
            JOIN schedulers schedule ON schedule.id = job.scheduler_id
              AND schedule.post_id = job.post_id
              AND schedule.user_id = job.user_id
              AND schedule.profile_id IS NOT DISTINCT FROM job.profile_id
            JOIN posts post ON post.id = job.post_id
              AND post.user_id = job.user_id
              AND post.profile_id IS NOT DISTINCT FROM job.profile_id
            WHERE job.id = %s
              AND job.status = 'pending'
              AND ({scope})
            FOR UPDATE OF job SKIP LOCKED
        )
        UPDATE publish_jobs AS job
        SET status = 'running',
            attempt = job.attempt + 1,
            claim_token = candidate.token,
            preflight_claim_token = candidate.token,
            external_started_at = NULL,
            locked_by = %s,
            locked_at = now(),
            started_at = COALESCE(job.started_at, now())
        FROM candidate
        WHERE job.id = candidate.id
        RETURNING job.id, job.claim_token
    """
    return query_db(query, (publish_job_id, *scope_args, worker_id), one=True)


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
        WHERE id = %s AND claim_token = %s
          AND preflight_claim_token = %s AND status = 'running'
        RETURNING id
        """,
        (publish_job_id, claim_token, claim_token),
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
        WHERE id = %s AND claim_token = %s
          AND preflight_claim_token = %s AND status = 'running'
          AND external_started_at IS NULL
        RETURNING id
        """,
        (publish_job_id, claim_token, claim_token),
        one=True,
    )
