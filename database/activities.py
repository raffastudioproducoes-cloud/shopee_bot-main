from psycopg.types.json import Jsonb
from shopee_bot.database import query_db, execute_db
from shopee_bot.database.activity_types import ActivityType


def query_activities_by_id(activity_id, user_id):
    """Retorna uma atividade pelo ID, restrita ao usuário dono."""
    query = """
        SELECT
            act.id AS id,
            act.metadata AS metadata,
            to_char(
                act.created_at - interval '3 hours',
                'DD/MM/YY HH24:MI:SS'
            ) AS localtime,
            act.created_at AS created_at,
            act_t.name AS name,
            act_t.description AS description
        FROM activities AS act
        LEFT JOIN activity_types AS act_t ON act_t.id = act.activity_id
        WHERE act.id = %s AND act.user_id = %s
    """
    args = (activity_id, user_id)
    return query_db(query, args, one=True)


def query_activities_all(user_id, limit=100):
    """Retorna todas as atividades de um usuário, ordenadas por data."""
    query = """
        SELECT
            act.id AS id,
            act.metadata AS metadata,
            to_char(
                act.created_at - interval '3 hours',
                'DD/MM/YY HH24:MI:SS'
            ) AS localtime,
            act.created_at AS created_at,
            act_t.name AS name,
            act_t.description AS description
        FROM activities AS act
        LEFT JOIN activity_types AS act_t ON act_t.id = act.activity_id
        WHERE act.user_id = %s
        ORDER BY act.created_at DESC
        LIMIT %s
    """
    args = (user_id, limit)
    return query_db(query, args)


def query_activities_paginated(user_id, cursor, limit):
    query = """
        SELECT
            act.id AS id,
            act.metadata AS metadata,
            to_char(
                act.created_at - interval '3 hours',
                'DD/MM/YY HH24:MI:SS'
            ) AS localtime,
            act.created_at AS created_at,
            act_t.name AS name,
            act_t.description AS description
        FROM activities AS act
        LEFT JOIN activity_types AS act_t ON act_t.id = act.activity_id
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                act.created_at < %s OR (act.created_at = %s AND act.id < %s)
            )
        ) AND act.user_id = %s
        ORDER BY act.created_at DESC
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
                user_id,
                limit
            ]
        except ValueError:
            # activities, next_cursor
            return [], None
    else:
        # Primeira página
        args = [None, None, None, None, user_id, limit]

    # Executa a query
    activities = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if activities and len(activities) == limit:
        last_item = activities[-1]
        next_cursor = f"{last_item['created_at']},{last_item['id']}"

    return activities, next_cursor


def activity_metadata_wrapper(data: dict):
    return {
        "metadata": data
    }


def insert_activities(
        user_id,
        activity_type_id: ActivityType,
        activity,
        open_conn=None,
        profile_id=None
):
    query = """
        INSERT INTO activities (metadata, activity_id, user_id, profile_id)
        VALUES (%s, %s, %s, %s)
    """
    args = (
        Jsonb(activity["metadata"]),
        activity_type_id.value,
        user_id,
        profile_id
    )
    return execute_db(query, args, open_conn)


def delete_activities(user_id, activity_id):
    query = """
        DELETE FROM activities
        WHERE id = %s AND user_id = %s
    """
    args = (activity_id, user_id)
    execute_db(query, args)
