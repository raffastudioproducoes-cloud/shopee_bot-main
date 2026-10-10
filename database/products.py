from datetime import datetime
import pytz
from shopee_bot.database import query_db, execute_db


def count(user_id):
    query = "SELECT COUNT(*) FROM products WHERE user_id = %s"
    return query_db(query, (user_id, ), True)["count"]


def count_by_id(user_id, ids=None):
    query = "SELECT COUNT(*) FROM products WHERE user_id = %s AND id = ANY(%s)"
    return query_db(query, (user_id, ids), True)["count"]


def get(user_id, product_id, profile_id=None):
    query = """
        SELECT id, product_id, name, original_link,
            commission_link, commission, image, price_min, price_max,
            created_at - interval '3 hours' AS created_at,
            updated_at - interval '3 hours' AS updated_at
        FROM products
        WHERE id = %s AND user_id = %s
          AND (%s::uuid IS NULL OR profile_id = %s::uuid)
    """
    args = (product_id, user_id, profile_id, profile_id)
    return query_db(query, args, True)


def gets(user_id, profile_id=None):
    query = """
        SELECT id, product_id, name, original_link,
            commission_link, commission, image, price_min, price_max,
            created_at - interval '3 hours' AS created_at,
            updated_at - interval '3 hours' AS updated_at
        FROM products
        WHERE user_id = %s
          AND (%s::uuid IS NULL OR profile_id = %s::uuid)
    """
    args = (user_id, profile_id, profile_id)
    return query_db(query, args)


def query_paginated_by_id(user_id, cursor, limit, ids=None):
    query = """
        SELECT id, product_id, name, original_link, commission_link,
            image, price_min, price_max, commission,
            created_at, updated_at
        FROM products
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                created_at < %s OR (created_at = %s AND id < %s)
            )
        ) AND user_id = %s AND id = ANY(%s)
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
                user_id,
                ids,
                limit
            ]
        except ValueError:
            # products, next_cursor
            return [], None
    else:
        # Primeira página
        args = [None, None, None, None, user_id, ids, limit]

    # Executa a query
    products = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if products and len(products) == limit:
        last_item = products[-1]
        created_at = str(last_item["created_at"])
        next_cursor = f"{created_at.replace(" ", "+")},{last_item['id']}"

    return products, next_cursor


def query_paginated_order_by_id(user_id, cursor, limit, ids=None):
    query = """
        SELECT id, product_id, name, original_link, commission_link,
               image, price_min, price_max, commission,
               created_at, updated_at, position
        FROM (
            SELECT id, product_id, name, original_link, commission_link,
                   image, price_min, price_max, commission,
                   created_at, updated_at,
                   COALESCE(array_position(%s, id), 999999) AS position
            FROM products
            WHERE user_id = %s
        ) sub
        WHERE (
            %s::INTEGER IS NULL OR (
                position > %s OR
                (position = %s AND created_at < %s) OR
                (position = %s AND created_at = %s AND id < %s)
            )
        )
        ORDER BY position ASC, created_at DESC, id DESC
        LIMIT %s
    """
    args = []

    if cursor:
        # cursor format "created_at,id,position"
        try:
            last_created_at, last_id, last_position = cursor.split(",")
            last_created_at = last_created_at.strip()
            last_id = int(last_id.strip())
            last_position = int(last_position.strip())
            args = [
                ids,
                user_id,
                last_position,
                last_position,
                last_position,
                last_created_at,
                last_position,
                last_created_at,
                last_id,
                limit
            ]
        except ValueError:
            # products, next_cursor
            return [], None
    else:
        # Primeira página
        args = [ids, user_id, None, None, None, None, None, None, None, limit]

    # Executa a query
    products = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if products and len(products) == limit:
        last_item = products[-1]
        created_at = str(last_item["created_at"])
        next_cursor = "{0},{1},{2}".format(
            created_at.replace(" ", "+"),
            last_item["id"],
            last_item["position"]
        )

    return products, next_cursor


def query_paginated(user_id, cursor, limit):
    query = """
        SELECT id, product_id, name, original_link, commission_link,
            image, price_min, price_max, commission,
            created_at, updated_at
        FROM products
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                created_at < %s OR (created_at = %s AND id < %s)
            )
        ) AND user_id = %s
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
    products = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if products and len(products) == limit:
        last_item = products[-1]
        created_at = str(last_item["created_at"])
        next_cursor = f"{created_at.replace(" ", "+")},{last_item['id']}"

    return products, next_cursor


def insert(user_id, product, open_conn=None):
    query = """
        INSERT INTO products(user_id, product_id, name, original_link,
        commission_link, commission, image, price_min, price_max)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    args = (
        user_id,
        product["product_id"],
        product["name"],
        product["original_link"],
        product["commission_link"],
        product["commission"],
        product["image"],
        product["price_min"],
        product["price_max"],
    )

    return execute_db(query, args, open_conn)


def update(user_id, product_id, product, open_conn=None, profile_id=None):
    query = """
        UPDATE products
        SET
            product_id = %s, name = %s, original_link = %s,
            commission_link = %s, commission = %s, image = %s, price_min = %s,
            price_max = %s, updated_at = %s
        WHERE id = %s AND user_id = %s
          AND (%s::uuid IS NULL OR profile_id = %s::uuid)
        RETURNING id
    """
    args = (
        product["product_id"],
        product["name"],
        product["original_link"],
        product["commission_link"],
        product["commission"],
        product["image"],
        product["price_min"],
        product["price_max"],
        # Atualiza o updated_at
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        product_id,
        user_id,
        profile_id,
        profile_id,
    )
    return execute_db(query, args, open_conn)


def delete(user_id, product_id, open_conn=None):
    query = """
        DELETE FROM products
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (product_id, user_id)
    execute_db(query, args, open_conn)
