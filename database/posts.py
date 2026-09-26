import pytz
from datetime import datetime
from shopee_bot.database import query_db, execute_db


def count(user_id):
    query = "SELECT COUNT(*) FROM posts WHERE user_id = %s AND post_id IS NULL"
    return query_db(query, (user_id, ), True)["count"]


def get(user_id, post_id):
    query = """
        WITH RECURSIVE post_hierarchy AS (
            -- parent node
            SELECT id, text, created_at, updated_at, post_id, 0 as depth
            FROM posts
            WHERE id = %s AND user_id = %s AND post_id IS NULL

            UNION ALL

            -- children nodes
            SELECT
                p.id, p.text, p.created_at, p.updated_at, p.post_id,
                ph.depth + 1
            FROM posts p
            INNER JOIN post_hierarchy ph ON p.post_id = ph.id
        )
        SELECT
            ph.id,
            ph.text,
            ph.created_at - interval '3 hours' AS created_at,
            ph.updated_at - interval '3 hours' AS updated_at,
            ph.post_id,
            ph.depth,
            COALESCE(
                array_agg(
                    -- duplicating because of LEFT JOINS
                    DISTINCT pp.product_id
                ) FILTER (WHERE pp.product_id IS NOT NULL),
                '{}'
            ) product_ids,
            COALESCE(
                array_agg(
                    -- using jsonb because of pyscopg3
                    DISTINCT jsonb_build_object(
                        'id', m.id,
                        'file_name', m.file_name,
                        'file_path', m.file_path,
                        'size', m.size,
                        'type', m.type
                    )
                ) FILTER (WHERE m.id IS NOT NULL),
                '{}'
            ) medias,
            COALESCE(
                json_build_object(
                    'id', s.id,
                    'func', s.func,
                    'trigger', s.trigger,
                    'time', to_char(s.time, 'HH24:MI'),
                    'day_of_week', s.day_of_week,
                    'start_date', s.start_date,
                    'run_date', s.run_date
                ),
                '{}'::json
            ) scheduler
        FROM post_hierarchy ph
        LEFT JOIN posts_products pp ON ph.id = pp.post_id
        LEFT JOIN posts_medias pm ON ph.id = pm.post_id
        LEFT JOIN medias m ON m.id = pm.media_id
        LEFT JOIN schedulers s ON s.post_id = ph.id
        GROUP BY
            ph.id, ph.text, ph.created_at, ph.updated_at, ph.post_id,
            ph.depth, pp.post_id, pm.post_id, s.id
        ORDER BY ph.depth ASC
    """
    args = (post_id, user_id)
    return query_db(query, args)


def get_for_delete(user_id, post_id):
    query = """
        WITH RECURSIVE post_hierarchy AS (
            SELECT id, 0 AS depth
            FROM posts
            WHERE id = %s AND user_id = %s AND post_id IS NULL

            UNION ALL

            SELECT p.id, ph.depth + 1
            FROM posts p
            INNER JOIN post_hierarchy ph ON p.post_id = ph.id
        )
        SELECT
            ph.id,
            ph.depth,
            COALESCE(
                array_agg(
                    json_build_object(
                        'file_path', m.file_path
                    )
                ) FILTER (WHERE m.id IS NOT NULL),
                '{}'
            ) AS medias,
            COALESCE(
                json_build_object('id', s.id),
                '{}'::json
            ) scheduler
        FROM post_hierarchy ph
        LEFT JOIN posts_medias pm ON ph.id = pm.post_id
        LEFT JOIN medias m ON pm.media_id = m.id
        LEFT JOIN schedulers s ON s.post_id = ph.id
        GROUP BY ph.id, ph.depth, s.id
        ORDER BY ph.depth;
    """
    args = (post_id, user_id)
    return query_db(query, args)


def query_paginated(user_id, cursor, limit):
    query = """
        WITH RECURSIVE post_hierarchy AS (
            -- Seleciona os posts raiz (onde post_id é NULL)
            SELECT id, id AS root_id, 0 AS depth
            FROM posts
            WHERE post_id IS NULL

            UNION ALL

            -- Seleciona os filhos recursivamente, mantendo o root_id
            SELECT p.id, ph.root_id, ph.depth + 1
            FROM posts p
            INNER JOIN post_hierarchy ph ON p.post_id = ph.id
        )
        SELECT
            p.id,
            p.text,
            p.created_at - interval '3 hours' AS created_at,
            p.updated_at - interval '3 hours' AS updated_at,
            COALESCE(
                array_agg(
                    json_build_object(
                        'id', m.id,
                        'file_name', m.file_name,
                        'file_path', m.file_path,
                        'size', m.size,
                        'type', m.type
                    )
                ) FILTER (WHERE m.id IS NOT NULL),
                '{}'
            ) medias,
            (
                SELECT COUNT(*)
                FROM post_hierarchy ph
                WHERE ph.root_id = p.id AND ph.depth > 0
            ) children,
            COALESCE(
                json_build_object(
                    'id', s.id,
                    'func', s.func,
                    'trigger', s.trigger,
                    'time', s.time,
                    'day_of_week', s.day_of_week,
                    'start_date', s.start_date,
                    'run_date', s.run_date
                ),
                '{}'::json
            ) scheduler
        FROM posts p
        LEFT JOIN posts_medias pm ON p.id = pm.post_id
        LEFT JOIN medias m ON m.id = pm.media_id
        LEFT JOIN schedulers s ON s.post_id = p.id
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                p.created_at < %s OR (
                    p.created_at = %s AND p.id < %s
                )
            )
        ) AND p.user_id = %s AND p.post_id IS NULL
        GROUP BY
            p.id,
            p.text,
            p.created_at,
            p.updated_at,
            pm.post_id,
            s.id
        ORDER BY p.created_at DESC, p.id DESC
        LIMIT %s;
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
            # products, next_cursor
            return [], None
    else:
        # Primeira página
        args = [None, None, None, None, user_id, limit]

    # Executa a query
    medias = query_db(query, args)

    next_cursor = None
    if medias and len(medias) == limit:
        last_item = medias[-1]
        next_cursor = f"{last_item['created_at']},{last_item['id']}"
    return medias, next_cursor


def insert(user_id, post, open_conn=None):
    query = """
        INSERT INTO posts(user_id, post_id, text, network)
        VALUES(%s, %s, %s, %s)
        RETURNING id
    """
    args = (
        user_id,
        post["post_id"] if "post_id" in post else None,
        post["text"],
        post.get("network") or "threads"
    )
    return execute_db(query, args, open_conn)


def update(user_id, post_id, post, open_conn=None):
    query = """
        UPDATE posts
        SET post_id = %s, text = %s, updated_at = %s,
            network = COALESCE(%s, network)
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        post["post_id"] if "post_id" in post else None,
        post["text"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        post.get("network"),
        post_id,
        user_id
    )
    return execute_db(query, args, open_conn)


def delete(user_id, post_id, open_conn=None):
    query = """
        DELETE FROM posts
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (post_id, user_id)
    execute_db(query, args, open_conn)
