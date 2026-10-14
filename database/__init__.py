import os
import psycopg
from psycopg import rows, Connection
from psycopg_pool import ConnectionPool
from shopee_bot.database.migrations import run_migrations
from shopee_bot.clogging import logger
from api.utils.log_sanitizer import sanitize_log_data
from dotenv import load_dotenv
load_dotenv()

HOST = os.environ.get("SHOPEE_PG_HOST")
DB = os.environ.get("SHOPEE_PG_DB")
USER = os.environ.get("SHOPEE_PG_USER")
PASSWORD = os.environ.get("SHOPEE_PG_PASSWORD")
# sslmode só é anexado quando definido (deploy externo exige require;
# local sem var mantém comportamento anterior).
SSLMODE = os.environ.get("SHOPEE_PG_SSLMODE")

_pool = None


def _dsn() -> str:
    from urllib.parse import quote_plus
    user = quote_plus(USER) if USER else ""
    pwd = quote_plus(PASSWORD) if PASSWORD else ""
    dsn = f"postgresql://{user}:{pwd}@{HOST}/{DB}"
    if SSLMODE:
        dsn += f"?sslmode={SSLMODE}"
    return dsn


def get_conn() -> Connection:
    global _pool

    conn = _pool.getconn()
    conn.set_autocommit(True)
    conn.row_factory = rows.dict_row

    return conn


def put_conn(conn: Connection):
    global _pool
    _pool.putconn(conn)


def query_db(query, args=(), one=False):
    conn = get_conn()
    with conn.cursor() as cur:
        rv = cur.execute(query, args).fetchall()
    put_conn(conn)
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), open_conn: Connection = None):
    """Executa INSERT/UPDATE/DELETE e devolve o id afetado, se houver.

    `cur.execute()` roda fora do try — erro real de SQL (violação de
    constraint, tipo não serializável, etc.) sobe pro chamador, não
    fica escondido. Só a falta de RETURNING (ex.: INSERT sem
    RETURNING) cai no fallback de LASTVAL().
    """
    conn = open_conn if open_conn else get_conn()
    last_id = None
    with conn.cursor() as cur:
        cur.execute(query, args)
        try:
            rv = cur.fetchone()
            if rv:
                last_id = rv["id"]
        except psycopg.ProgrammingError:
            rv = cur.execute("SELECT LASTVAL()").fetchone()
            last_id = rv["lastval"]

    if not open_conn:
        put_conn(conn)
    return last_id


def close_connection(exception=None):
    global _pool
    if _pool is not None:
        logger.debug("closing pool...")
        _pool.close()


def init():
    global _pool
    logger.debug("opening pool connection...")
    logger.debug(sanitize_log_data(f"postgresql://{USER}:{PASSWORD}@{HOST}/{DB}"))
    _pool = ConnectionPool(
        _dsn(),
        min_size=1,
        max_size=10,
        timeout=30,
        open=True,
        check=ConnectionPool.check_connection,
    )
    run_migrations()
