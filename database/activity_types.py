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


def query_activity_types_by_id(activity_type_id):
    """Retorna um tipo de atividade pelo ID, ou None se não existir."""
    query = """
        SELECT id, name, description, created_at, updated_at
        FROM activity_types
        WHERE id = %s
    """
    args = (activity_type_id, )
    return query_db(query, args, one=True)


def query_activity_types_all():
    """Retorna todos os tipos de atividade, ordenados por nome."""
    query = """
        SELECT id, name, description, created_at, updated_at
        FROM activity_types
        ORDER BY name
    """
    return query_db(query)


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
        activity_type["description"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        activity_type_id
    )
    return execute_db(query, args, open_conn)


def delete_activity_types(activity_type_id, user_id=None):
    """Deleta um tipo de atividade.

    Args:
        activity_type_id: ID do tipo de atividade no banco.
        user_id: ID do usuário dono do registro. Obrigatório.
            Sem esse parâmetro a função não deve ser chamada.
    """
    if user_id is None:
        raise ValueError("user_id é obrigatório")
    query = """
        DELETE FROM activity_types
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (activity_type_id, user_id)
    execute_db(query, args)
