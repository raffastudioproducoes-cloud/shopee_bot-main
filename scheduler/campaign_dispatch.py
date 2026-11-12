"""F4E campaign worker: separate origin, database claim, no APScheduler mirrors.

A missing/expired commercial entitlement, paused reservation or lost claim
blocks the last external-delivery barrier. Unknown outcomes are never retried.
"""
import socket
from datetime import timedelta
from contextvars import ContextVar

from shopee_bot.database import query_db
from shopee_bot.database.scheduler_environment import current_environment
from shopee_bot.scheduler.publication_result import PublicationResult, unknown, failed
from shopee_bot.clogging import logger
from api.utils.log_sanitizer import sanitize_log_data

_campaign_attempt = ContextVar("campaign_attempt", default=None)

PUBLISHERS = {
    "threads": "bot_post",
    "x": "bot_post_x",
    "facebook": "bot_post_facebook",
    "instagram": "bot_post_instagram",
    "tiktok": "bot_post_tiktok",
}


def campaign_execution_enabled():
    return _campaign_attempt.get() is not None


def _call(fn, args, *, one=True):
    placeholders = ",".join("%s" for _ in args)
    result = query_db(f"SELECT public.{fn}({placeholders}) AS result", tuple(args), one=one)
    return result["result"] if result else None


def mark_external_started(job_id, claim_token):
    """Called at the last durable boundary, under reservation row lock."""
    attempt = _campaign_attempt.get()
    if not attempt or str(attempt["publish_job_id"]) != str(job_id):
        return False
    return _call(
        "mark_campaign_external_f4e",
        (current_environment(), str(job_id), str(claim_token)),
    ) is True


def _validated_credentials(network, user_id, profile_id):
    # Not a publish call: tests the live provider permissions and refreshes tokens.
    from shopee_bot.api.routers.credentials import _autotest_outcome
    try:
        state, _ = _autotest_outcome(network, user_id, profile_id)
    except Exception as exc:
        logger.warning(
            "Falha na verificação OAuth da campanha %s (%s): %s",
            network, type(exc).__name__, sanitize_log_data(str(exc)),
            exc_info=True,
        )
        return False
    return state == "ok"


CREDENTIAL_RETRY_WINDOW = timedelta(minutes=60)
CREDENTIAL_MAX_ATTEMPTS = 2  # o claim já soma 1 a cada tentativa: 1 original + 1 retentativa


def retry_credential_failure(job_id):
    """Devolve à fila (uma vez) slot que falhou só por credencial/OAuth.

    Só se: ainda dentro de 60 min de scheduled_for, attempt < 2, sem external_id,
    sem chamada externa iniciada. O attempt não é somado aqui: o claim já o faz.
    Retorna True se recolocou em 'pending'.
    """
    job = query_db(
        "SELECT status, attempt, external_id, external_started_at, scheduled_for, now() AS db_now "
        "FROM public.publish_jobs WHERE id = %s AND publication_origin = 'campaign'",
        (str(job_id),), one=True,
    )
    if not job or job["status"] != "failed" or job["external_id"] or job["external_started_at"]:
        return False
    if job["attempt"] >= CREDENTIAL_MAX_ATTEMPTS or not job["scheduled_for"]:
        return False
    if job["db_now"] - job["scheduled_for"] > CREDENTIAL_RETRY_WINDOW:
        return False
    # Um único statement: job e slot voltam juntos (o claim exige slot 'planned' + job 'pending').
    requeued = query_db(
        """
        WITH j AS (
            UPDATE public.publish_jobs
            SET status = 'pending', finished_at = NULL
            WHERE id = %s AND publication_origin = 'campaign' AND status = 'failed'
              AND external_id IS NULL AND external_started_at IS NULL AND attempt < %s
            RETURNING id
        )
        UPDATE public.campaign_network_slots_f4e s
        SET state = 'planned', finished_at = NULL
        FROM j WHERE s.publish_job_id = j.id
        RETURNING s.publish_job_id
        """,
        (str(job_id), CREDENTIAL_MAX_ATTEMPTS), one=True,
    )
    if requeued:
        logger.info("Campanha %s recolocada na fila após falha de credencial", job_id)
    return bool(requeued)


def drain():
    from shopee_bot.scheduler import is_shutting_down
    if is_shutting_down():
        return
    env = current_environment()
    try:
        _call("pause_expired_campaigns_f4e", (env,))
        _call("recover_campaign_publications_f4e", (env,))
        _call("close_completed_campaigns_f4e", (env,))
    except Exception:
        logger.exception("Não foi possível recuperar campanhas; nenhum envio de campanha nesta rodada")
        return

    from shopee_bot.scheduler import (
        bot_post, bot_post_x, bot_post_facebook, bot_post_instagram, bot_post_tiktok,
    )
    publishers = {
        "threads": bot_post, "x": bot_post_x, "facebook": bot_post_facebook,
        "instagram": bot_post_instagram, "tiktok": bot_post_tiktok,
    }
    for _ in range(10):
        if is_shutting_down():
            return
        try:
            claim = _call("claim_campaign_publication_f4e", (env, socket.gethostname()[:150]))
        except Exception:
            logger.exception("Claim da fila campaign falhou")
            return
        if not claim:
            return
        token = _campaign_attempt.set(claim)
        from shopee_bot.scheduler import publication_context
        context = publication_context.activate(
            claim["publish_job_id"], claim["claim_token"], None,
        )
        status, external_id, error = "unknown", None, None
        credential_failure = False
        try:
            if not _validated_credentials(
                claim["network"], claim["user_id"], claim["profile_id"],
            ):
                credential_failure = True
                result = failed("Credenciais ou permissões OAuth inválidas")
            else:
                result = publishers[claim["network"]](claim["scheduler_id"])
            if not isinstance(result, PublicationResult):
                result = unknown("Rede não confirmou a publicação")
            status, external_id, error = result.status, result.external_id, result.error
            if status not in ("succeeded","failed","unknown"):
                status, error = "unknown", "Resultado de rede inválido"
        except publication_context.PublicationDeferred:
            # Lost claim or pause before network. Lease recovery decides safe retry.
            logger.warning("Campanha %s interrompida antes do envio", claim["publish_job_id"])
            status = None
            continue
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)
            logger.exception("Publicador de campanha levantou exceção")
        finally:
            publication_context.reset(context)
            _campaign_attempt.reset(token)
            if status:
                try:
                    _call("finish_campaign_publication_f4e", (
                        env,claim["publish_job_id"],claim["claim_token"],
                        status, str(external_id) if external_id else None,
                        sanitize_log_data(str(error))[:2000] if error else None,
                    ))
                except Exception:
                    logger.exception("Resultado de campanha não persistido; recuperação manterá estado incerto")
                else:
                    if credential_failure and status == "failed":
                        try:
                            retry_credential_failure(claim["publish_job_id"])
                        except Exception:
                            logger.exception("Retentativa de campanha não agendada; slot permanece failed")
