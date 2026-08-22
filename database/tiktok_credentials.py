from datetime import datetime
import pytz
from shopee_bot.database import query_db, execute_db
from shopee_bot.utils.crypto import encrypt, decrypt


def get_by_user_id(user_id):
    query = """
        SELECT
            u.username username,
            tc.app_id tiktok_app_id,
            tc.secret tiktok_secret,
            tc.status tiktok_status
        FROM users u
        LEFT JOIN tiktok_credentials tc ON tc.user_id = u.id
        WHERE u.id = %s
    """
    args = (user_id, )
    result = query_db(query, args, True)
    if result:
        result["tiktok_secret"] = decrypt(result["tiktok_secret"])
    return result


def insert(user_id, credential, open_conn=None):
    query = """
        INSERT INTO tiktok_credentials(user_id, app_id, secret, status)
        VALUES(%s, %s, %s, %s)
    """
    args = (
        user_id,
        credential["app_id"],
        encrypt(credential["secret"]),
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
        UPDATE tiktok_credentials
        SET app_id = %s, secret = %s, status = %s, updated_at = %s
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        credential["app_id"],
        encrypt(credential["secret"]),
        credential["status"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        credential_id,
        user_id
    )
    return execute_db(query, args, open_conn)
