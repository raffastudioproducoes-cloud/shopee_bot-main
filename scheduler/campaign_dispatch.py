"""F4E campaign worker: separate origin, database claim, no APScheduler mirrors.

A missing/expired commercial entitlement, paused reservation or lost claim
blocks the last external-delivery barrier. Unknown outcomes are never retried.
"""
import socket
from contextvars import ContextVar

from shopee_bot.database import query_db
from shopee_bot.database.scheduler_environment import current_environment
from shopee_bot.scheduler.publication_result import PublicationResult, unknown, failed
from shopee_bot.clogging import logger
from shopee_bot.utils.log_sanitizer import sanitize_log_data

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
        logger.warning("Falha na verificação OAuth da campanha %s (%s)", network, type(exc).__name__)
        return False
    return state == "ok"


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
        try:
            if not _validated_credentials(
                claim["network"], claim["user_id"], claim["profile_id"],
            ):
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
