from shopee_bot.database import execute_db, query_db
from shopee_bot.database.scheduler_environment import current_environment
from shopee_bot.database.central_dispatch import central_dispatch_enabled, publication_scope_sql, new_schedule_dispatch_mode
from shopee_bot.database.scheduler_environment import publication_executor_environment


def _execution_scope(alias, *, legacy_only=False):
    """Legado local permanece isolado; central só na produção com gate ativo."""
    if not central_dispatch_enabled():
        return (
            f"{alias}.environment = %s AND {alias}.dispatch_mode = 'legacy' AND {alias}.publication_origin = 'legacy'",
            (current_environment(),),
        )
    if legacy_only:
        return (
            f"{alias}.environment = %s AND {alias}.dispatch_mode = 'legacy' AND {alias}.publication_origin = 'legacy'",
            (current_environment(),),
        )
    scope, args = publication_scope_sql(alias)
    return f"({scope}) AND {alias}.publication_origin = 'legacy'", args

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
    from shopee_bot.scheduler import campaign_dispatch
    if campaign_dispatch.campaign_execution_enabled():
        scope = "s.environment = %s AND s.publication_origin = 'campaign'"
        scope_args = (current_environment(),)
    else:
        scope, scope_args = _execution_scope("s")
    query = f"""
        SELECT
            s.id, s.post_id, s.user_id, s.profile_id, s.func, s.trigger,
            s.time, s.day_of_week, s.days_of_week, s.start_date, s.run_date,
            s.environment, s.dispatch_mode, s.dispatch_cancelled_at,
            s.publication_origin
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
        WHERE user_id = %s AND publication_origin = 'legacy'
    """
    args = (user_id, )
    return query_db(query, args)


def insert(user_id, job, open_conn=None):
    # Sem gate, preservar o INSERT legado e a ordem original dos parâmetros.
    # A migration 068 atribui dispatch_mode='legacy' pelo DEFAULT do banco.
    mode = new_schedule_dispatch_mode()
    columns = (
        "post_id, user_id, func, trigger, time, day_of_week, days_of_week, "
        "start_date, run_date, profile_id, environment"
    )
    values = "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
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
        current_environment(),
    )
    if mode == "central":
        columns += ", dispatch_mode"
        values += ", %s"
        args += (mode,)

    query = f"INSERT INTO schedulers ({columns}) VALUES({values}) RETURNING id"
    return execute_db(query, args, open_conn)


def delete(user_id, scheduler_id, open_conn=None):
    # A remoção física é legada: para central, usar cancel_central()
    # para preservar publish_jobs (FK ON DELETE CASCADE).
    query = """
        DELETE FROM schedulers
        WHERE id = %s AND user_id = %s AND dispatch_mode = 'legacy'
          AND publication_origin = 'legacy'
        RETURNING id
    """
    args = (scheduler_id, user_id)
    return execute_db(query, args, open_conn)


def list_central_dispatch_jobs():
    """Somente produção lista intenções centrais; legacy nunca é copiado."""
    if (
        not central_dispatch_enabled()
        or current_environment() != publication_executor_environment()
    ):
        return []
    return query_db(
        """
        SELECT
            s.id, s.post_id, s.user_id, s.profile_id, s.environment,
            s.func, s.trigger, s.time, s.day_of_week, s.days_of_week,
            s.start_date, s.run_date, s.dispatch_revision
        FROM schedulers s
        JOIN posts p ON p.id = s.post_id
          AND p.user_id = s.user_id
          AND p.profile_id IS NOT DISTINCT FROM s.profile_id
        WHERE s.dispatch_mode = 'central'
          AND s.publication_origin = 'legacy'
          AND s.dispatch_cancelled_at IS NULL
          AND s.func = ANY(%s)
          AND (
              s.trigger = 'cron'
              OR (
                  s.trigger = 'date'
                  AND s.run_date >= (
                      now() AT TIME ZONE 'America/Sao_Paulo'
                  ) - INTERVAL '1 hour'
                  AND NOT EXISTS (
                      SELECT 1 FROM publish_jobs pj
                      WHERE pj.scheduler_id = s.id
                  )
              )
          )
        ORDER BY s.id
        """,
        (list(NETWORK_FUNC_MAP.values()),),
    )


def cancel_central(user_id, scheduler_id, open_conn=None):
    """Cancela apenas agendas centrais da origem atual, SEM apagar histórico."""
    if not central_dispatch_enabled():
        return None
    return execute_db(
        """
        UPDATE schedulers
        SET dispatch_cancelled_at = now(),
            dispatch_revision = dispatch_revision + 1
        WHERE id = %s AND user_id = %s AND environment = %s
          AND dispatch_mode = 'central' AND publication_origin = 'legacy'
          AND dispatch_cancelled_at IS NULL
        RETURNING id
        """,
        (scheduler_id, user_id, current_environment()),
        open_conn,
    )


def expedite_central(job_id):
    """Fluxo 'Agora' idempotente: um único UUID de agenda e de ocorrência.

    Chamadas repetidas devolvem o mesmo ID; nunca criam um segundo job.
    Apenas antecipa enquanto ainda não existe entrada em publish_jobs.
    """
    if not central_dispatch_enabled():
        return None
    return execute_db(
        """
        UPDATE schedulers s
        SET run_date = CASE
                WHEN s.run_date > (now() AT TIME ZONE 'America/Sao_Paulo')
                     AND NOT EXISTS (
                         SELECT 1 FROM publish_jobs pj WHERE pj.scheduler_id = s.id
                     )
                  THEN now() AT TIME ZONE 'America/Sao_Paulo'
                ELSE s.run_date
            END,
            dispatch_revision = s.dispatch_revision + CASE
                WHEN s.run_date > (now() AT TIME ZONE 'America/Sao_Paulo')
                     AND NOT EXISTS (
                         SELECT 1 FROM publish_jobs pj WHERE pj.scheduler_id = s.id
                     )
                  THEN 1 ELSE 0
            END
        WHERE s.id = %s AND s.environment = %s
          AND s.dispatch_mode = 'central'
          AND s.publication_origin = 'legacy'
          AND s.dispatch_cancelled_at IS NULL
          AND s.trigger = 'date'
        RETURNING id
        """,
        (job_id, current_environment()),
    )


def expire_missed_central_dates(grace_seconds=3600):
    """Grava falha terminal de data única vencida sem chamada externa.

    Nunca reenvia a publicação. Usa idempotency_key=UUID da agenda,
    a mesma chave do executor date, e só toca central/sem histórico.
    """
    if (
        not central_dispatch_enabled()
        or current_environment() != publication_executor_environment()
    ):
        return []
    return query_db(
        """
        INSERT INTO publish_jobs (
            scheduler_id, post_id, user_id, profile_id, network,
            idempotency_key, status, last_error, finished_at
        )
        SELECT
            s.id, s.post_id, s.user_id, s.profile_id,
            CASE s.func
                WHEN 'bot_post' THEN 'threads'
                WHEN 'bot_post_x' THEN 'x'
                WHEN 'bot_post_facebook' THEN 'facebook'
                WHEN 'bot_post_instagram' THEN 'instagram'
                WHEN 'bot_post_tiktok' THEN 'tiktok'
            END,
            s.id::text, 'failed',
            'Horário de publicação expirado sem executor; envio não realizado',
            now()
        FROM schedulers s
        JOIN posts p ON p.id = s.post_id
          AND p.user_id = s.user_id
          AND p.profile_id IS NOT DISTINCT FROM s.profile_id
        WHERE s.dispatch_mode = 'central'
          AND s.publication_origin = 'legacy'
          AND s.dispatch_cancelled_at IS NULL
          AND s.trigger = 'date'
          AND s.func = ANY(%s)
          AND s.run_date < (
              now() AT TIME ZONE 'America/Sao_Paulo'
          ) - make_interval(secs => %s)
          AND NOT EXISTS (
              SELECT 1 FROM publish_jobs pj WHERE pj.scheduler_id = s.id
          )
        ON CONFLICT (idempotency_key) DO NOTHING
        RETURNING scheduler_id, status
        """,
        (list(NETWORK_FUNC_MAP.values()), grace_seconds),
    )
