from shopee_bot.database import execute_db, query_db
from shopee_bot.database.scheduler_environment import current_environment
from shopee_bot.database.central_dispatch import central_dispatch_enabled, publication_scope_sql


def _execution_scope(alias, *, legacy_only=False):
    """Legado local permanece isolado; central só na produção com gate ativo."""
    if not central_dispatch_enabled():
        return f"{alias}.environment = %s", (current_environment(),)
    if legacy_only:
        return (
            f"{alias}.environment = %s AND {alias}.dispatch_mode = 'legacy'",
            (current_environment(),),
        )
    return publication_scope_sql(alias)

# Rede social do post -> função de publicação chamada pelo scheduler
# (ver scheduler/__init__.py, que resolve o nome via globals()).
# Kwai fica de fora: sem API pública confirmada ainda. Os wrappers
# bot_post_x/facebook/instagram/tiktok ainda não existem — apontar pra
# eles é seguro, só falha se alguém agendar post com essa rede antes
# do wrapper ser criado.
NETWORK_FUNC_MAP = {
    "threads": "bot_post",
    "x": "bot_post_x",
    "facebook": "bot_post_facebook",
    "instagram": "bot_post_instagram",
    "tiktok": "bot_post_tiktok",
}


def get_publication_jobs():
    # Upgrade dos jobs locais pré-existentes. Os futuros espelhos centrais
    # terão IDs distintos no APScheduler e reconciliação própria.
    scope, scope_args = _execution_scope("s", legacy_only=True)
    query = f"""
        SELECT s.id
        FROM schedulers s
        JOIN posts p ON p.id = s.post_id
          AND p.user_id = s.user_id
          AND p.profile_id IS NOT DISTINCT FROM s.profile_id
        WHERE s.func = ANY(%s)
          AND {scope}
    """
    return query_db(query, (list(NETWORK_FUNC_MAP.values()), *scope_args))


def get_by_post_id(user_id, post_id):
    query = """
        SELECT
            id, post_id, user_id, func, trigger, time, day_of_week, days_of_week,
            start_date, run_date
        FROM schedulers
        WHERE post_id = %s AND user_id = %s
    """
    args = (post_id, user_id)
    return query_db(query, args, True)


def get_by_id(job_id):
    scope, scope_args = _execution_scope("s")
    query = f"""
        SELECT
            s.id, s.post_id, s.user_id, s.profile_id, s.func, s.trigger,
            s.time, s.day_of_week, s.days_of_week, s.start_date, s.run_date,
            s.environment
        FROM schedulers s
        JOIN posts p ON p.id = s.post_id
          AND p.user_id = s.user_id
          AND p.profile_id IS NOT DISTINCT FROM s.profile_id
        WHERE s.id = %s AND ({scope})
    """
    args = (job_id, *scope_args)
    return query_db(query, args, True)


def query(user_id):
    query = """
        SELECT
            id, post_id, user_id, func, trigger, time, day_of_week, days_of_week,
            start_date, run_date
        FROM schedulers
        WHERE user_id = %s
    """
    args = (user_id, )
    return query_db(query, args)


def insert(user_id, job, open_conn=None):
    query = """
        INSERT INTO schedulers (
            post_id, user_id, func, trigger, time, day_of_week, days_of_week,
            start_date, run_date, profile_id, environment
        )
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    args = (
        job["post_id"],
        user_id,
        job["func"],
        job["trigger"],
        job["time"] if "time" in job else None,
        job["day_of_week"] if "day_of_week" in job else None,
        job["days_of_week"] if "days_of_week" in job else None,
        job["start_date"] if "start_date" in job else None,
        job["run_date"] if "run_date" in job else None,
        job.get("profile_id"),
        current_environment()
    )
    return execute_db(query, args, open_conn)


def delete(user_id, scheduler_id, open_conn=None):
    query = """
        DELETE FROM schedulers
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (scheduler_id, user_id)
    return execute_db(query, args, open_conn)
