import os
import socket
from datetime import datetime

import pytz
from dotenv import load_dotenv
from psycopg import Connection
from psycopg.pq import TransactionStatus

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.gevent import GeventScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from shopee_bot.database import get_conn, put_conn, publication_claims, publish_jobs, schedulers
from shopee_bot.database.scheduler_environment import current_environment, publication_executor_environment
from shopee_bot.database.central_dispatch import central_dispatch_enabled
from shopee_bot.scheduler import central_reconciler
from shopee_bot.clogging import logger
from shopee_bot.database.activities import insert_activities, activity_metadata_wrapper
from shopee_bot.database.activity_types import ActivityType
# dynamic called functions | DO NOT REMOVE
from shopee_bot.scheduler.bot_post import bot_post
from shopee_bot.scheduler.bot_post_facebook import bot_post_facebook
from shopee_bot.scheduler.bot_post_instagram import bot_post_instagram
from shopee_bot.scheduler.bot_post_tiktok import bot_post_tiktok
from shopee_bot.scheduler.bot_post_x import bot_post_x
from shopee_bot.scheduler.update_products import update_products
from shopee_bot.scheduler.publication_result import PublicationResult, unknown
from shopee_bot.scheduler import publication_context

load_dotenv()
HOST = os.environ.get("SHOPEE_PG_HOST")
DB = os.environ.get("SHOPEE_PG_DB")
USER = os.environ.get("SHOPEE_PG_USER")
PASSWORD = os.environ.get("SHOPEE_PG_PASSWORD")
REDIS_HOST = os.environ.get("REDIS_HOST")

_scheduler = None
_shutting_down = False


def mark_shutting_down() -> None:
    """O SIGTERM do Gunicorn impede novos disparos antes do drain."""
    global _shutting_down
    _shutting_down = True


def is_shutting_down() -> bool:
    return _shutting_down


def shutdown_gracefully() -> None:
    """Stop new triggers and wait for in-flight publish jobs on worker exit.

    Platform termination deadlines may still cut this short; in that case the
    durable queue deliberately remains unknown instead of blindly retrying.
    """
    global _scheduler
    mark_shutting_down()
    current = _scheduler
    if current is None or not current.running:
        return
    current.pause()
    current.shutdown(wait=True)
    _scheduler = None


# Job "date" com run_date = agora (botão "Agora" do front) chega ao
# scheduler alguns ms/s depois do horário e o default do APScheduler
# (misfire_grace_time=1s) descartava com "was missed by 0:00:01".
# 5 min de tolerância + coalesce (várias execuções perdidas viram uma).
JOB_DEFAULTS = {"misfire_grace_time": 3600, "coalesce": True}
PUBLICATION_CLAIM_LEASE_SECONDS = 600
PUBLISH_JOB_LEASE_SECONDS = 600

MISSED_JOB_MESSAGE = "Horário de publicação perdido (servidor ocupado ou reiniciando). Publique de novo."
PROFILE_SCOPED_FUNCS = frozenset({
    "bot_post", "bot_post_x", "bot_post_facebook", "bot_post_instagram", "bot_post_tiktok",
})
NETWORK_BY_FUNC = {
    "bot_post": "threads",
    "bot_post_x": "x",
    "bot_post_facebook": "facebook",
    "bot_post_instagram": "instagram",
    "bot_post_tiktok": "tiktok",
}


def scheduler_enabled() -> bool:
    return os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"


def scheduler_ready() -> bool:
    """Requer flag ativa e instância realmente inicializada, sem shutdown."""
    return (
        scheduler_enabled()
        and not _shutting_down
        and _scheduler is not None
        and _scheduler.running
    )


def request_wakeup() -> bool:
    """Solicita verificação dos horários ao scheduler já inicializado."""
    current = _scheduler

    if not scheduler_enabled() or _shutting_down:
        return False

    if current is None or not current.running:
        return False

    current.wakeup()
    return True


def _scheduled_function(func: str):
    return execute_publication if func in PROFILE_SCOPED_FUNCS else globals()[func]


def execute_central_publication(job_id):
    """A barreira protege inclusive mirrors persistidos após desligar o gate."""
    if (
        _shutting_down
        or not central_dispatch_enabled()
        or current_environment() != publication_executor_environment()
    ):
        logger.warning("Mirror central ignorado fora da autoridade: %s", job_id)
        return
    job = schedulers.get_by_id(job_id)
    if not job or job.get("dispatch_mode") != "central":
        logger.warning("Mirror central sem intenção ativa autorizada: %s", job_id)
        return
    execute_publication(job_id)


def reconcile_central_jobs():
    if (
        _scheduler is None
        or not central_dispatch_enabled()
        or current_environment() != publication_executor_environment()
    ):
        return
    for expired in schedulers.expire_missed_central_dates(
        central_reconciler.MISFIRE_SECONDS
    ):
        logger.warning("Agenda central expirada sem envio: %s", expired["scheduler_id"])
    central_reconciler.reconcile(_scheduler, execute_central_publication)


def _occurrence_key(job_id, job_data):
    """A agenda date ocorre uma vez; cron ganha uma chave por minuto local."""
    if job_data.get("trigger") != "cron":
        return str(job_id)
    return f"{job_id}:{datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%dT%H:%M')}"


def _execute_publish_item(publish_job_id, job_data):
    queue_claim = publish_jobs.claim(
        publish_job_id, socket.gethostname(), PUBLISH_JOB_LEASE_SECONDS
    )
    if not queue_claim:
        logger.info("Fila de publicacao %s esta em execucao em outro worker", publish_job_id)
        return

    context_token = publication_context.activate(
        publish_job_id, queue_claim["claim_token"], queue_claim.get("content_snapshot")
    )
    try:
        try:
            result = globals()[job_data["func"]](job_data["id"])
        except publication_context.PublicationDeferred:
            # SIGTERM/claim perdido antes da fronteira externa: pode retomar.
            if not publish_jobs.requeue_if_safe(
                publish_job_id, queue_claim["claim_token"]
            ):
                logger.warning(
                    "Publicacao %s nao pode ser devolvida a fila; requer conciliacao",
                    publish_job_id,
                )
            return
        except Exception as exc:
            publish_jobs.finish(
                publish_job_id, queue_claim["claim_token"], "unknown",
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        if not isinstance(result, PublicationResult):
            result = unknown("Publicador nao confirmou o desfecho da publicacao")
        publish_jobs.finish(
            publish_job_id, queue_claim["claim_token"], result.status,
            external_id=result.external_id, error=result.error,
        )
    finally:
        publication_context.reset(context_token)


def drain_publish_jobs():
    """Retoma apenas pendentes recentes; antigos expiram sem envio tardio."""
    for item in publish_jobs.expire_stale_pending():
        logger.warning("Fila de publicacao %s expirou sem envio externo", item["id"])
    expired = publish_jobs.expire_running(PUBLISH_JOB_LEASE_SECONDS)
    for item in expired:
        logger.warning(
            "Fila de publicacao %s saiu do lease com status %s",
            item["id"], item["status"],
        )
    for item in publish_jobs.recoverable(PUBLISH_JOB_LEASE_SECONDS):
        job_data = schedulers.get_by_id(item["scheduler_id"])
        if not job_data:
            logger.warning("Fila %s aponta para agenda removida", item["id"])
            continue
        _execute_publish_item(item["id"], job_data)


def execute_publication(job_id):
    """Executa uma publicacao somente quando esta instancia detem o lease."""
    if _shutting_down:
        logger.info("Ignorando novo disparo durante encerramento: %s", job_id)
        return
    job_data = schedulers.get_by_id(job_id)
    if not job_data:
        logger.warning("Job de publicacao %s nao encontrado neste ambiente", job_id)
        return

    claim_token = publication_claims.try_claim(job_id, PUBLICATION_CLAIM_LEASE_SECONDS)
    if not claim_token:
        logger.info("Job de publicacao %s ja esta em execucao em outra instancia", job_id)
        return

    try:
        item = publish_jobs.enqueue(
            scheduler_id=job_id,
            post_id=job_data["post_id"],
            user_id=job_data["user_id"],
            profile_id=job_data.get("profile_id"),
            network=NETWORK_BY_FUNC[job_data["func"]],
            idempotency_key=_occurrence_key(job_id, job_data),
        )
        if item["status"] in publish_jobs.TERMINAL_STATUSES:
            logger.info("Publicacao %s ja teve desfecho %s", job_id, item["status"])
            return

        _execute_publish_item(item["id"], {**job_data, "id": job_id})
    finally:
        try:
            publication_claims.release(job_id, claim_token)
        except Exception:
            logger.exception("Falha ao liberar lease de publicacao %s", job_id)


def _upgrade_existing_publication_jobs():
    """Faz agendas persistidas antes do deploy usarem o lease ao reiniciar."""
    for job_data in schedulers.get_publication_jobs():
        job_id = str(job_data["id"])
        try:
            _scheduler.modify_job(
                job_id,
                jobstore="default",
                func=execute_publication,
                args=(job_id,),
                misfire_grace_time=JOB_DEFAULTS["misfire_grace_time"],
            )
        except JobLookupError:
            logger.info("Job de publicacao %s nao existe mais no jobstore", job_id)


def _on_job_problem(event):
    """Registra falha de publicação que escapou do try/except dos bots
    (ex.: credencial ausente antes do loop) ou job perdido — sem isso o
    usuário via "Publicação disparada" e nada acontecia, sem rastro em
    Atividade."""
    try:
        original_id = (
            event.job_id[len(central_reconciler.PREFIX):]
            if str(event.job_id).startswith(central_reconciler.PREFIX)
            else event.job_id
        )
        job_data = schedulers.get_by_id(original_id)
        if not job_data or not job_data.get("post_id"):
            return
        if event.code == EVENT_JOB_MISSED:
            error = MISSED_JOB_MESSAGE
        else:
            exc = event.exception
            error = f"{type(exc).__name__}: {exc}"[:300]
        insert_activities(
            job_data["user_id"],
            ActivityType.BOT_POST_FAILURE,
            activity_metadata_wrapper({
                "network": NETWORK_BY_FUNC.get(job_data.get("func"), "unknown"),
                "job_id": str(event.job_id),
                "post_id": job_data["post_id"],
                "stage": "scheduler",
                "error": error,
            }),
            profile_id=job_data.get("profile_id"),
        )
    except Exception:
        logger.exception(f"falha ao registrar erro do job #{event.job_id}")


def _remove_job(user_id, job_id, conn):
    global _scheduler
    if central_dispatch_enabled() and schedulers.cancel_central(user_id, job_id, conn):
        # O job central será removido do espelho de produção no tick de
        # reconciliação. Mesmo se disparar antes, get_by_id o bloqueia.
        return
    schedulers.delete(user_id, job_id, conn)

    job = _scheduler.get_job(job_id)
    if job:
        _scheduler.remove_job(job_id)


def remove_job(user_id, job_id, open_conn=None):
    global _scheduler

    conn: Connection = open_conn if open_conn else get_conn()

    # 2 = INTRANS
    if conn.info.transaction_status == TransactionStatus(2):
        _remove_job(user_id, job_id, conn)
    else:
        with conn.transaction():
            _remove_job(user_id, job_id, conn)

    if not open_conn:
        put_conn(conn)


def run_job(job_id):
    global _scheduler

    if central_dispatch_enabled() and schedulers.expedite_central(job_id):
        # Não executa no staging: intenção durável lida pela produção.
        reconcile_central_jobs()
        return

    # Job "date" ainda pendente (fluxo "Agora": post criado com run_date de
    # segurança, mídia enviada, e só então disparado): antecipa o próprio
    # job em vez de criar uma cópia on_demand — senão publicava 2 vezes.
    pending = _scheduler.get_job(str(job_id), jobstore="default")
    if pending and isinstance(pending.trigger, DateTrigger):
        pending.modify(next_run_time=datetime.now(_scheduler.timezone))
        return

    job_data = schedulers.get_by_id(job_id)
    if not job_data:
        raise ValueError("Agenda nao encontrada neste ambiente")
    func = job_data["func"]

    _scheduler.add_job(
        jobstore="on_demand",
        id=job_id,
        func=_scheduled_function(func),
        args=(job_id, ),
        trigger="date",
    )


def _add_job(user_id, job, conn):
    global _scheduler

    func = job["func"]
    trigger = job["trigger"]
    if func in PROFILE_SCOPED_FUNCS and not job.get("profile_id"):
        raise ValueError("profile_id obrigatorio para publicacao em rede social")
    job_id = schedulers.insert(user_id, job, conn)

    if central_dispatch_enabled():
        # Sem jobstore local de staging e sem segunda chamada ao provedor.
        # O executor de produção materializará a intenção persistida.
        return str(job_id)

    if trigger == "cron":
        minute = job["time"].minute
        hour = job["time"].hour
        start_date = job["start_date"] if "start_date" in job else None
        days = job.get("days_of_week") or [job["day_of_week"]]
        # APScheduler aceita a lista como expressão cron. Jobs legados seguem
        # chegando só com day_of_week e continuam sendo executados iguais.
        days_expression = ",".join(str(day) for day in days)

        _scheduler.add_job(
            id=str(job_id),
            func=_scheduled_function(func),
            args=(job_id, ),
            trigger=trigger,
            minute=minute,
            hour=hour,
            day_of_week=days_expression,
            start_date=start_date
        )
    elif trigger == "date":
        _scheduler.add_job(
            id=str(job_id),
            func=_scheduled_function(func),
            args=(job_id, ),
            trigger=trigger,
            run_date=job["run_date"]
        )
    else:
        raise ValueError(f"trigger de agenda não suportado: {trigger}")

    # A API precisa do ID real para desfazer uma agenda de múltiplos
    # horários caso a criação de um dos próximos jobs falhe.
    return str(job_id)


def add_job(user_id, job, open_conn=None):
    global _scheduler

    conn: Connection = open_conn if open_conn else get_conn()

    try:
        # 2 = INTRANS; preserve a transaction supplied by the caller.
        if conn.info.transaction_status == TransactionStatus(2):
            return _add_job(user_id, job, conn)
        with conn.transaction():
            return _add_job(user_id, job, conn)
    finally:
        if not open_conn:
            put_conn(conn)


def _jobstore_dsn() -> str:
    from urllib.parse import quote_plus
    user = quote_plus(USER) if USER else ""
    pwd = quote_plus(PASSWORD) if PASSWORD else ""
    sslmode = os.environ.get("SHOPEE_PG_SSLMODE")
    dsn = f"postgresql+psycopg://{user}:{pwd}@{HOST}/{DB}"
    if sslmode:
        dsn += f"?sslmode={sslmode}"
    return dsn


def _run_daily_analytics_refresh():
    """Evita carregar a API e validar segredos no import do scheduler legado.

    A validação de API_SECRET_KEY permanece no boot da API; aqui a dependência
    só é importada quando o job interno realmente executa.
    """
    from api.analytics_refresh import refresh_due_analytics
    refresh_due_analytics()


def init():
    global _scheduler, _shutting_down
    _shutting_down = False
    environment = current_environment()
    logger.info("Scheduler initializing in %s...", environment)

    _scheduler = GeventScheduler(
        jobstores={
            "default": SQLAlchemyJobStore(
                url=_jobstore_dsn(),
                tablename=("apscheduler_jobs_staging" if environment == "staging" else "apscheduler_jobs"),
            ),
            "on_demand": MemoryJobStore()
        },
        executors={
            "default": ThreadPoolExecutor(20),
            "on_demand": ThreadPoolExecutor(5)
        },
        job_defaults=JOB_DEFAULTS,
        timezone=pytz.timezone("America/Sao_Paulo"),
        logger=logger
    )
    _scheduler.add_listener(_on_job_problem, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    
    # Inicializa pausado para atualizar os jobs persistidos
    # antes de avaliar execuções atrasadas.
    _scheduler.start(paused=True)
    
    _upgrade_existing_publication_jobs()

    if (
        central_dispatch_enabled()
        and environment == publication_executor_environment()
    ):
        # Reconciliador único: não criar outro cron no Supabase.
        reconcile_central_jobs()
        _scheduler.add_job(
            reconcile_central_jobs,
            trigger="interval",
            seconds=30,
            jobstore="on_demand",
            id="central_reconciliation",
            replace_existing=True,
            max_instances=1,
        )

    _scheduler.add_job(
        drain_publish_jobs,
        trigger="interval",
        minutes=1,
        id="publish_queue_recovery",
        replace_existing=True,
    )
    
    # Job em memória por instância; o claim SQL evita coleta duplicada quando
    # staging e main compartilham o Supabase. Após suspensão Free, roda na
    # próxima hora ativa (a abertura das Análises também faz catch-up).
    _scheduler.add_job(
        _run_daily_analytics_refresh,
        trigger="interval",
        hours=1,
        id="analytics_refresh_daily",
        jobstore="on_demand",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler.resume()
