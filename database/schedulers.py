from shopee_bot.database import execute_db, query_db


def get_by_post_id(user_id, post_id):
    query = """
        SELECT
            id, post_id, user_id, func, trigger, time, day_of_week,
            start_date, run_date
        FROM schedulers
        WHERE post_id = %s AND user_id = %s
    """
    args = (post_id, user_id)
    return query_db(query, args, True)


def get_by_id(job_id):
    query = """
        SELECT
            id, post_id, user_id, func, trigger, time, day_of_week,
            start_date, run_date
        FROM schedulers
        WHERE id = %s
    """
    args = (job_id, )
    return query_db(query, args, True)


def query(user_id):
    query = """
        SELECT
            id, post_id, user_id, func, trigger, time, day_of_week,
            start_date, run_date
        FROM schedulers
        WHERE user_id = %s
    """
    args = (user_id, )
    return query_db(query, args)


def insert(user_id, job, open_conn=None):
    query = """
        INSERT INTO schedulers (
            post_id, user_id, func, trigger, time, day_of_week, start_date,
            run_date
        )
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    args = (
        job["post_id"],
        user_id,
        job["func"],
        job["trigger"],
        job["time"] if "time" in job else None,
        job["day_of_week"] if "day_of_week" in job else None,
        job["start_date"] if "start_date" in job else None,
        job["run_date"] if "run_date" in job else None
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
