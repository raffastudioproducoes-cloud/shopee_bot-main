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
            tc.app_id tiktok_app_id,
            tc.secret tiktok_secret,
            tc.status tiktok_status,
            tc.user_access_token tiktok_user_access_token,
            tc.refresh_token tiktok_refresh_token,
            tc.open_id tiktok_open_id
        FROM users u
        LEFT JOIN tiktok_credentials tc ON tc.user_id = u.id
            AND (%s::uuid IS NULL OR tc.profile_id = %s::uuid)
        WHERE u.id = %s
    """
    args = (profile_id, profile_id, user_id)
    result = query_db(query, args, True)
    if result:
        result["tiktok_secret"] = decrypt(result["tiktok_secret"])
        # user_access_token/refresh_token são gravados pelo fluxo OAuth
        # (api/routers/credentials.py::tiktok_callback, via API nova) —
        # podem não existir ainda se o usuário só salvou Client Key/
        # Secret e nunca completou a autorização.
        result["tiktok_user_access_token"] = decrypt(
            result["tiktok_user_access_token"]
        )
        result["tiktok_refresh_token"] = decrypt(result["tiktok_refresh_token"])
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
