from datetime import datetime
import pytz
from shopee_bot.database import query_db, execute_db


def get_by_user_id(user_id):
    query = """
        SELECT
            u.username AS username,
            tc.t_user_id AS threads_user_id,
            tc.access_token AS threads_access_token,
            tc.status AS threads_status
        FROM users u
        LEFT JOIN threads_credentials tc ON tc.user_id = u.id
        WHERE u.id = %s
    """
    args = (user_id, )
    return query_db(query, args, True)


def insert(user_id, credential, open_conn=None):
    query = """
        INSERT INTO threads_credentials(user_id, t_user_id, access_token,
            status)
        VALUES(%s, %s, %s, %s)
    """
    args = (
        user_id,
        credential["t_user_id"],
        credential["access_token"],
        credential["status"]
    )
    return execute_db(query, args, open_conn)


def update(
    user_id,
    credential_id,
    credential,
    open_conn=None
):
    query = """
        UPDATE threads_credentials
        SET t_user_id = %s, access_token = %s, status = %s, updated_at = %s
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        credential["t_user_id"],
        credential["access_token"],
        credential["status"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        credential_id,
        user_id
    )
    return execute_db(query, args, open_conn)
