from datetime import datetime, timedelta
import pytz
from shopee_bot.database import query_db, execute_db
from shopee_bot.utils.crypto import encrypt, decrypt


def get_by_user_id(user_id, profile_id=None):
    """`profile_id` opcional: com perfil, usa a credencial DO PERFIL; sem
    perfil (job antigo), comportamento anterior (por user_id)."""
    query = """
        SELECT
            u.username username,
            xc.app_id x_app_id,
            xc.secret x_secret,
            xc.status x_status,
            xc.user_access_token x_access_token,
            xc.user_refresh_token x_refresh_token,
            xc.token_expires_at token_expires_at
        FROM users u
        LEFT JOIN x_credentials xc ON xc.user_id = u.id
            AND (%s::uuid IS NULL OR xc.profile_id = %s::uuid)
        WHERE u.id = %s
    """
    args = (profile_id, profile_id, user_id)
    result = query_db(query, args, True)
    if result:
        result["x_secret"] = decrypt(result["x_secret"])
        result["x_access_token"] = decrypt(result["x_access_token"])
        result["x_refresh_token"] = decrypt(result["x_refresh_token"])
    return result


def insert(user_id, credential, open_conn=None):
    query = """
        INSERT INTO x_credentials(user_id, app_id, secret, status)
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
        UPDATE x_credentials
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


def update_tokens(user_id, profile_id, tokens, open_conn=None):
    """Persiste access/refresh token de usuário renovados via
    api.x_oauth.refresh_access_token. Usado pelo scheduler (bot_post_x) antes
    de publicar, quando token_expires_at já passou."""
    query = """
        UPDATE x_credentials
        SET user_access_token = %s, user_refresh_token = %s,
            token_expires_at = %s, updated_at = %s
        WHERE user_id = %s
          AND (%s::uuid IS NULL OR profile_id = %s::uuid)
        RETURNING id
    """
    expires_at = datetime.now(pytz.utc) + timedelta(
        seconds=tokens.get("expires_in", 7200)
    )
    args = (
        encrypt(tokens["access_token"]),
        encrypt(tokens.get("refresh_token")),
        expires_at,
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        user_id,
        profile_id,
        profile_id,
    )
    return execute_db(query, args, open_conn)
