import os
from datetime import datetime

import pytz
from dotenv import load_dotenv
from psycopg import Connection
from psycopg.pq import TransactionStatus

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.gevent import GeventScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from shopee_bot.database import get_conn, put_conn, schedulers
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

load_dotenv()
HOST = os.environ.get("SHOPEE_PG_HOST")
DB = os.environ.get("SHOPEE_PG_DB")
USER = os.environ.get("SHOPEE_PG_USER")
PASSWORD = os.environ.get("SHOPEE_PG_PASSWORD")
REDIS_HOST = os.environ.get("REDIS_HOST")

_scheduler = None

# Job "date" com run_date = agora (botão "Agora" do front) chega ao
# scheduler alguns ms/s depois do horário e o default do APScheduler
# (misfire_grace_time=1s) descartava com "was missed by 0:00:01".
# 5 min de tolerância + coalesce (várias execuções perdidas viram uma).
JOB_DEFAULTS = {"misfire_grace_time": 300, "coalesce": True}

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


def _on_job_problem(event):
    """Registra falha de publicação que escapou do try/except dos bots
    (ex.: credencial ausente antes do loop) ou job perdido — sem isso o
    usuário via "Publicação disparada" e nada acontecia, sem rastro em
    Atividade."""
    try:
        job_data = schedulers.get_by_id(event.job_id)
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

    # Job "date" ainda pendente (fluxo "Agora": post criado com run_date de
    # segurança, mídia enviada, e só então disparado): antecipa o próprio
    # job em vez de criar uma cópia on_demand — senão publicava 2 vezes.
    pending = _scheduler.get_job(str(job_id), jobstore="default")
    if pending and isinstance(pending.trigger, DateTrigger):
        pending.modify(next_run_time=datetime.now(_scheduler.timezone))
        return

    job_data = schedulers.get_by_id(job_id)
    func = job_data["func"]

    _scheduler.add_job(
        jobstore="on_demand",
        id=job_id,
        func=globals()[func],
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
            func=globals()[func],
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
            func=globals()[func],
            args=(job_id, ),
            trigger=trigger,
            run_date=job["run_date"]
        )


def add_job(user_id, job, open_conn=None):
    global _scheduler

    conn: Connection = open_conn if open_conn else get_conn()

    # 2 = INTRANS
    if conn.info.transaction_status == TransactionStatus(2):
        _add_job(user_id, job, conn)
    else:
        with conn.transaction():
            _add_job(user_id, job, conn)

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


def init():
    global _scheduler
    logger.info("Scheduler initializing...")

    _scheduler = GeventScheduler(
        jobstores={
            "default": SQLAlchemyJobStore(
                url=_jobstore_dsn()
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
    _scheduler.start()
