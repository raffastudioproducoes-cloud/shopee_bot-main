from enum import StrEnum
from shopee_bot.database import query_db, execute_db


class MediaType(StrEnum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


def get_for_delete(user_id):
    query = """
        SELECT file_path
        FROM medias
        WHERE user_id = %s
    """
    args = (user_id, )
    return query_db(query, args)


def insert(user_id, media, open_conn=None):
    query = """
        INSERT INTO medias(user_id, file_name, file_path, size, type)
        VALUES(%s, %s, %s, %s, %s)
        RETURNING id
    """
    args = (
        user_id,
        media["file_name"],
        media["file_path"],
        media["size"],
        media["type"]
    )
    return execute_db(query, args, open_conn)


def delete(user_id, media_id, open_conn=None):
    query = """
        DELETE FROM medias
        WHERE id = %s and user_id = %s
        RETURNING id
    """
    args = (media_id, user_id)
    execute_db(query, args, open_conn)
