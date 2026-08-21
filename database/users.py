import os
import pytz
import bcrypt
from datetime import datetime
from shopee_bot.database import get_conn, put_conn, query_db, execute_db, \
    medias
from shopee_bot.utils.crypto import decrypt


def count():
    query = "SELECT COUNT(*) FROM users"
    return query_db(query, (), True)["count"]


def get(user_id):
    query = """
        SELECT
            id::text, username, access,
            created_at - interval '3 hours' AS created_at,
            updated_at - interval '3 hours' AS updated_at
        FROM users
        WHERE id = %s
    """
    args = (user_id, )
    return query_db(query, args, True)


def get_by_username(username):
    query = """
        SELECT id, username, password, access
        FROM users
        WHERE username = %s
    """
    args = (username, )
    return query_db(query, args, True)


def get_credentials(user_id):
    query = """
        SELECT
            u.username username,
            sc.id shopee_id,
            sc.app_id shopee_app_id,
            sc.secret shopee_secret,
            sc.status shopee_status,
            tc.id threads_id,
            tc.t_user_id AS threads_user_id,
            tc.access_token AS threads_access_token,
            tc.status AS threads_status
        FROM users u
        LEFT JOIN shopee_credentials sc ON sc.user_id = u.id
        LEFT JOIN threads_credentials tc ON tc.user_id = u.id
        WHERE u.id = %s
    """
    args = (user_id, )
    result = query_db(query, args, True)
    if result:
        result["shopee_secret"] = decrypt(result["shopee_secret"])
        result["threads_access_token"] = decrypt(
            result["threads_access_token"]
        )
    return result


def query_paginated(cursor, limit):
    query = """
        SELECT id, username, access, created_at, updated_at
        FROM users
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                created_at < %s OR (created_at = %s AND id < %s)
            )
        )
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """
    args = []

    if cursor:
        # cursor format "created_at,id"
        try:
            last_created_at, last_id = cursor.split(",")
            last_created_at = last_created_at.strip()
            last_id = int(last_id.strip())
            args = [
                last_created_at,
                last_created_at,
                last_created_at,
                last_id,
                limit
            ]
        except ValueError:
            # users, next_cursor
            return [], None
    else:
        # Primeira página
        args = [None, None, None, None, limit]

    # Executa a query
    users = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if users and len(users) == limit:
        last_item = users[-1]
        next_cursor = f"{last_item['created_at']},{last_item['id']}"

    return users, next_cursor


def insert(user, open_conn=None):
    query = """
        INSERT INTO users(id, username, password, access)
        VALUES (gen_random_uuid(), %s, %s, %s)
        RETURNING id
    """
    hashed_password = bcrypt.hashpw(
        user["password"].encode("ascii"),
        bcrypt.gensalt()
    )
    args = (
        user["username"],
        hashed_password.decode("ascii"),
        user["access"],
    )
    return execute_db(query, args, open_conn)


def update(user_id, user, open_conn=None):
    query = """
        UPDATE users
        SET username = %s, access = %s, updated_at = %s
        WHERE id = %s
        RETURNING id
    """
    args = (
        user["username"],
        user["access"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        user_id
    )
    return execute_db(query, args, open_conn)


def update_password(user_id, password, open_conn=None):
    query = """
        UPDATE users
        SET password = %s, updated_at = %s
        WHERE id = %s
        RETURNING id
    """
    hashed_password = bcrypt.hashpw(
        password.encode("ascii"),
        bcrypt.gensalt()
    )
    args = (
        hashed_password.decode("ascii"),
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        user_id
    )
    return execute_db(query, args, open_conn)


def delete(user_id, open_conn=None):
    # get data before cascade deletion
    medias_data = medias.get_for_delete(user_id)

    conn = get_conn()
    with conn.transaction():
        query = """
            DELETE FROM users
            WHERE id = %s
            RETURNING id
        """
        args = (user_id,)
        execute_db(query, args, conn)

        # delete all user related data
        for media in medias_data:
            file_path = media["file_path"]
            os.remove(file_path)

    put_conn(conn)
