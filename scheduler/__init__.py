import os
import pytz
from dotenv import load_dotenv
from psycopg import Connection
from psycopg.pq import TransactionStatus

from apscheduler.schedulers.gevent import GeventScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from shopee_bot.database import get_conn, put_conn, schedulers
from shopee_bot.clogging import logger
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
    job_id = schedulers.insert(user_id, job, conn)

    if trigger == "cron":
        minute = job["time"].minute
        hour = job["time"].hour
        start_date = job["start_date"] if "start_date" in job else None

        _scheduler.add_job(
            id=str(job_id),
            func=globals()[func],
            args=(job_id, ),
            trigger=trigger,
            minute=minute,
            hour=hour,
            day_of_week=job["day_of_week"],
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
        timezone=pytz.timezone("America/Sao_Paulo"),
        logger=logger
    )
    _scheduler.start()
