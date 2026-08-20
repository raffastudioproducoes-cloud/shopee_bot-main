from shopee_bot.database import query_db, execute_db


def get_file_paths_diff(post_id, media_ids):
    query = """
        SELECT m.file_path
        FROM posts_medias pm
        LEFT JOIN medias m ON pm.media_id = m.id
        WHERE NOT EXISTS (
            SELECT 1 FROM unnest(%s::integer[]) AS excluded_id
            WHERE excluded_id = pm.media_id
        ) AND post_id = %s
    """
    args = (media_ids, post_id)
    return query_db(query, args)


def get_next_display_order(post_id):
    query = """
        SELECT COALESCE(MAX(display_order + 1), 0) next_display_order
        FROM posts_medias
        WHERE post_id = %s
    """
    args = (post_id, )
    return query_db(query, args, True)["next_display_order"]


def insert(post_media, open_conn=None):
    query = """
        INSERT INTO posts_medias(post_id, media_id, display_order)
        VALUES(%s, %s, %s)
    """
    args = (
        post_media["post_id"],
        post_media["media_id"],
        post_media["display_order"]
    )
    return execute_db(query, args, open_conn)


def update(post_media, open_conn=None):
    query = """
        UPDATE posts_medias
        SET display_order = %s
        WHERE post_id = % AND media_id = %s
    """
    args = (
        post_media["display_order"],
        post_media["post_id"],
        post_media["media_id"]
    )
    return execute_db(query, args, open_conn)


def delete(post_id, media_id, open_conn=None):
    query = """
        DELETE FROM posts_medias
        WHERE post_id = %s AND media_id = %s
    """
    args = (post_id, media_id)
    execute_db(query, args, open_conn)


def delete_media_diff(post_id, media_ids, open_conn=None):
    query = """
        DELETE FROM posts_medias
        WHERE NOT EXISTS (
            SELECT 1 FROM unnest(%s::integer[]) AS excluded_id
            WHERE excluded_id = media_id
        ) AND post_id = %s
        RETURNING 0 id
    """
    args = (media_ids, post_id)
    execute_db(query, args, open_conn)
