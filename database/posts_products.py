from shopee_bot.database import execute_db


def insert(post_product, open_conn=None):
    query = """
        INSERT INTO posts_products(post_id, product_id, display_order)
        VALUES(%s, %s, %s)
    """
    args = (
        post_product["post_id"],
        post_product["product_id"],
        post_product["display_order"]
    )
    return execute_db(query, args, open_conn)


def update(post_product, open_conn=None):
    query = """
        UPDATE posts_products
        SET display_order = %s
        WHERE post_id = %s AND product_id = %s
    """
    args = (
        post_product["display_order"],
        post_product["post_id"],
        post_product["product_id"]
    )
    return execute_db(query, args, open_conn)


def delete(post_id, product_id, open_conn=None):
    query = """
        DELETE FROM posts_products
        WHERE post_id = %s AND product_id = %s
    """
    args = (
        post_id,
        product_id
    )
    execute_db(query, args, open_conn)


def delete_product_diff(post_id, product_ids, open_conn=None):
    query = """
        DELETE FROM posts_products
        WHERE NOT EXISTS (
            SELECT 1 FROM unnest(%s::integer[]) AS excluded_id
            WHERE excluded_id = product_id
        ) AND post_id = %s
        RETURNING 0 id
    """
    args = (product_ids, post_id)
    execute_db(query, args, open_conn)
