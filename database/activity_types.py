from datetime import datetime
from enum import Enum
import pytz
from shopee_bot.database import query_db, execute_db


class ActivityType(Enum):
    BOT_POST_SUCCESS = 1
    BOT_POST_FAILURE = 2
    BOT_RESET_SUCCESS = 3
    BOT_RESET_FAILURE = 4
    BOT_LOGIN_SUCCESS = 5
    BOT_LOGIN_FAILURE = 6

    SCHEDULER_START = 7
    SCHEDULER_SUCCESS = 8
    SCHEDULER_FAILURE = 9
    SCHEDULER_INFO = 10


def query_activity_types(query, args=(), one=False):
    result = query_db(query, args, one)
    return result


def insert_activity_types(activity_type, open_conn=None):
    query = """
        INSERT INTO activity_types (name, description)
        VALUES (%s, %s)
    """
    args = (
        activity_type["name"],
        activity_type["description"]
    )
    return execute_db(query, args, open_conn)


def update_activity_types(activity_type_id, activity_type, open_conn=None):
    query = """
        UPDATE activity_types
        SET name = %s, description = %s, updated_at = %s
        WHERE id = %s
        RETURNING id
    """
    args = (
        activity_type["name"],
        activity_type_id["description"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        activity_type_id
    )
    return execute_db(query, args, open_conn)


def delete_activity_types(activity_type_id):
    query = """
        DELETE FROM activity_types
        WHERE id = %s
        RETURNING id
    """
    args = (activity_type_id, )
    execute_db(query, args)
