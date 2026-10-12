from psycopg.types.json import Jsonb
from shopee_bot.database import query_db, execute_db
from shopee_bot.database.activity_types import ActivityType
from api.utils.log_sanitizer import sanitize_log_data


_PUBLISH_ACTIVITY_TYPES = {
    ActivityType.BOT_POST_SUCCESS,
    ActivityType.BOT_POST_FAILURE,
}


def _log_action(*args, **kwargs):
    """Import tardio para não acoplar o startup do scheduler ao FastAPI.

    O helper de auditoria é best-effort e já absorve indisponibilidade do
    Supabase. Mantemos a importação aqui para os testes do scheduler seguirem
    isolados do bootstrap da API.
    """
    from api.audit_log import log_action

    return log_action(*args, **kwargs)


def _record_publish_business_log(user_id, profile_id, activity_type, metadata):
    """Espelha o resultado real da rede no painel administrativo de Logs.

    A tabela ``activities`` continua sendo a fonte da tela Posts. Este espelho
    dá ao administrador o mesmo desfecho (rede, post, job, etapa e erro) sem
    texto do post, credenciais ou payloads de autorização.
    """
    if activity_type not in _PUBLISH_ACTIVITY_TYPES:
        return

    action = (
        "post_publish_succeeded"
        if activity_type is ActivityType.BOT_POST_SUCCESS
        else "post_publish_failed"
    )
    fields = []
    for key in ("network", "post_id", "job_id", "stage", "part_index", "total_parts", "published_parts"):
        value = metadata.get(key)
        if value is not None:
            fields.append(f"{key}={value}")
    if metadata.get("error"):
        fields.append(f"error={metadata['error']}")

    try:
        _log_action(action, " ".join(fields), user_id=user_id, profile_id=profile_id)
    except Exception:
        # Auditoria adicional nunca pode derrubar a publicação nem esconder
        # a atividade principal já persistida acima.
        pass


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
        "metadata": sanitize_log_data(data)
    }


def insert_activities(
        user_id,
        activity_type_id: ActivityType,
        activity,
        open_conn=None,
        profile_id=None
):
    # Defesa no ponto de persistência: mesmo um chamador que esqueça o
    # activity_metadata_wrapper não consegue gravar uma credencial no JSONB.
    metadata = sanitize_log_data(activity["metadata"])
    query = """
        INSERT INTO activities (metadata, activity_id, user_id, profile_id)
        VALUES (%s, %s, %s, %s)
    """
    args = (
        Jsonb(metadata),
        activity_type_id.value,
        user_id,
        profile_id
    )
    result = execute_db(query, args, open_conn)
    _record_publish_business_log(user_id, profile_id, activity_type_id, metadata)
    return result


def delete_activities(user_id, activity_id):
    query = """
        DELETE FROM activities
        WHERE id = %s AND user_id = %s
    """
    args = (activity_id, user_id)
    execute_db(query, args)
