from datetime import datetime
import pytz
from shopee_bot.database import query_db, execute_db
from shopee_bot.utils.crypto import encrypt, decrypt


def get_by_user_id(user_id):
    query = """
        SELECT
            u.username username,
            kc.app_id kwai_app_id,
            kc.secret kwai_secret,
            kc.status kwai_status
        FROM users u
        LEFT JOIN kwai_credentials kc ON kc.user_id = u.id
        WHERE u.id = %s
    """
    args = (user_id, )
    result = query_db(query, args, True)
    if result:
        result["kwai_secret"] = decrypt(result["kwai_secret"])
    return result


def insert(user_id, credential, open_conn=None):
    query = """
        INSERT INTO kwai_credentials(user_id, app_id, secret, status)
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
        UPDATE kwai_credentials
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
