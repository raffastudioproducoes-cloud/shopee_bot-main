from datetime import datetime
import pytz
from shopee_bot.database import query_db, execute_db
from shopee_bot.utils.crypto import encrypt, decrypt


def get_by_user_id(user_id, profile_id=None):
    """`profile_id` opcional: com perfil, usa a credencial DO PERFIL; sem
    perfil (job antigo), comportamento anterior (por user_id)."""
    query = """
        SELECT
            u.username username,
            fc.app_id facebook_app_id,
            fc.secret facebook_secret,
            fc.page_id facebook_page_id,
            fc.page_name facebook_page_name,
            fc.page_access_token facebook_page_access_token,
            fc.status facebook_status
        FROM users u
        LEFT JOIN facebook_credentials fc ON fc.user_id = u.id
            AND (%s::uuid IS NULL OR fc.profile_id = %s::uuid)
        WHERE u.id = %s
    """
    args = (profile_id, profile_id, user_id)
    result = query_db(query, args, True)
    if result:
        result["facebook_secret"] = decrypt(result["facebook_secret"])
        result["facebook_page_access_token"] = decrypt(result["facebook_page_access_token"])
    return result


def insert(user_id, credential, open_conn=None):
    query = """
        INSERT INTO facebook_credentials(user_id, app_id, secret, page_id,
            status)
        VALUES(%s, %s, %s, %s, %s)
    """
    args = (
        user_id,
        credential["app_id"],
        encrypt(credential["secret"]),
        credential.get("page_id"),
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
        UPDATE facebook_credentials
        SET app_id = %s, secret = %s, page_id = %s, status = %s,
            updated_at = %s
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        credential["app_id"],
        encrypt(credential["secret"]),
        credential.get("page_id"),
        credential["status"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        credential_id,
        user_id
    )
    return execute_db(query, args, open_conn)
