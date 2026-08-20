from datetime import datetime
import pytz
from shopee_bot.database import query_db, execute_db


def get_by_user_id(user_id):
    query = """
        SELECT
            u.username username,
            sc.app_id shopee_app_id,
            sc.secret shopee_secret,
            sc.status shopee_status
        FROM users u
        LEFT JOIN shopee_credentials sc ON sc.user_id = u.id
        WHERE u.id = %s
    """
    args = (user_id, )
    return query_db(query, args, True)


def insert(user_id, credential, open_conn=None):
    query = """
        INSERT INTO shopee_credentials(user_id, app_id, secret, status)
        VALUES(%s, %s, %s, %s)
    """
    args = (
        user_id,
        credential["app_id"],
        credential["secret"],
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
        UPDATE shopee_credentials
        SET app_id = %s, secret = %s, status = %s, updated_at = %s
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        credential["app_id"],
        credential["secret"],
        credential["status"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        credential_id,
        user_id
    )
    return execute_db(query, args, open_conn)
