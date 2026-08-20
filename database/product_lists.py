import pytz
from datetime import datetime
from psycopg import Connection
from psycopg.pq import TransactionStatus
from shopee_bot.database import query_db, execute_db, get_conn, put_conn


def count(user_id):
    query = "SELECT COUNT(*) FROM product_lists WHERE user_id = %s"
    return query_db(query, (user_id, ), True)["count"]


def get(user_id, product_list_id):
    query = """
        SELECT
            pl.id,
            pl.name,
            pl.created_at - interval '3 hours' created_at,
            pl.updated_at - interval '3 hours' updated_at,
            COALESCE(
                array_agg(p.id) FILTER (WHERE p.id IS NOT NULL),
                '{}'
            ) AS list
        FROM product_lists pl
        LEFT JOIN product_lists_products plp ON pl.id = plp.product_list_id
        LEFT JOIN products p ON p.id = plp.product_id
        WHERE pl.id = %s AND pl.user_id = %s
        GROUP BY pl.id, pl.name, pl.created_at, pl.updated_at, pl.user_id
    """
    args = (product_list_id, user_id)
    return query_db(query, args, True)


def query_paginated_by_id(user_id, cursor, limit, ids=None):
    query = """
        SELECT
            pl.id AS id,
            pl.name AS name,
            pl.created_at - interval '3 hours' AS created_at,
            pl.updated_at - interval '3 hours' AS updated_at,
            COALESCE(
                array_agg(
                    json_build_object(
                        'id', p.id,
                        'image', p.image,
                        'name', p.name,
                        'price_min', p.price_min,
                        'price_max', p.price_max,
                        'commission', p.commission,
                        'commission_link', p.commission_link,
                        'original_link', p.original_link
                    )
                ) FILTER (WHERE p.product_id IS NOT NULL),
                '{}'
            ) AS list
        FROM product_lists AS pl
        LEFT JOIN product_lists_products plp ON pl.id = plp.product_list_id
        LEFT JOIN products p ON p.id = plp.product_id
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                pl.created_at < %s OR (
                    pl.created_at = %s AND pl.id < %s
                )
            )
        ) AND pl.user_id = %s AND id = ANY(%s)
        GROUP BY pl.id, pl.name, pl.created_at, pl.updated_at, pl.user_id
        ORDER BY pl.created_at DESC, pl.id DESC
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
                ids,
                limit
            ]
        except ValueError:
            # products, next_cursor
            return [], None
    else:
        # Primeira ágina
        args = [None, None, None, None, user_id, ids, limit]

    # Executa a query
    product_lists = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if product_lists and len(product_lists) == limit:
        last_item = product_lists[-1]
        next_cursor = f"{last_item['created_at']},{last_item['id']}"

    return product_lists, next_cursor


def query_paginated(user_id, cursor, limit):
    query = """
        SELECT
            pl.id AS id,
            pl.name AS name,
            pl.created_at - interval '3 hours' AS created_at,
            pl.updated_at - interval '3 hours' AS updated_at,
            COALESCE(
                array_agg(
                    json_build_object(
                        'id', p.id,
                        'image', p.image,
                        'name', p.name,
                        'price_min', p.price_min,
                        'price_max', p.price_max,
                        'commission', p.commission,
                        'commission_link', p.commission_link,
                        'original_link', p.original_link
                    )
                ) FILTER (WHERE p.product_id IS NOT NULL),
                '{}'
            ) AS list
        FROM product_lists AS pl
        LEFT JOIN product_lists_products plp ON pl.id = plp.product_list_id
        LEFT JOIN products p ON p.id = plp.product_id
        WHERE (
            %s::TIMESTAMP IS NULL OR (
                pl.created_at < %s OR (
                    pl.created_at = %s AND pl.id < %s
                )
            )
        ) AND pl.user_id = %s
        GROUP BY pl.id, pl.name, pl.created_at, pl.updated_at, pl.user_id
        ORDER BY pl.created_at DESC, pl.id DESC
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
    product_lists = query_db(query, args)

    # Determina o próximo cursor
    next_cursor = None
    if product_lists and len(product_lists) == limit:
        last_item = product_lists[-1]
        next_cursor = f"{last_item['created_at']},{last_item['id']}"

    return product_lists, next_cursor


def insert(user_id, product_list, open_conn=None):
    query = """
        INSERT INTO product_lists(user_id, name)
        VALUES (%s, %s)
    """
    args = (
        user_id,
        product_list["name"],
    )

    return execute_db(query, args, open_conn)


def update(user_id, product_list_id, product_list, open_conn=None):
    query = """
        UPDATE product_lists
        SET name = %s, updated_at = %s
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (
        product_list["name"],
        datetime.now(pytz.timezone('America/Sao_Paulo')),
        product_list_id,
        user_id
    )
    return execute_db(query, args, open_conn)


def delete(user_id, product_list_id, open_conn=None):
    query = """
        DELETE FROM product_lists
        WHERE id = %s AND user_id = %s
        RETURNING id
    """
    args = (product_list_id, user_id)
    execute_db(query, args, open_conn)


def delete_with_products(user_id, product_list_id, open_conn=None):
    conn: Connection = open_conn if open_conn else get_conn()

    query = """
        SELECT
            COALESCE(
                array_agg(p.id) FILTER (WHERE p.id IS NOT NULL),
                '{}'
            ) AS ids
        FROM product_lists pl
        LEFT JOIN product_lists_products plp ON pl.id = plp.product_list_id
        LEFT JOIN products p ON p.id = plp.product_id
        WHERE pl.id = %s AND pl.user_id = %s
    """
    args = (product_list_id, user_id)
    product_ids = query_db(query, args, True)["ids"]

    if not product_ids or len(product_ids) == 0:
        delete(user_id, product_list_id, conn)
        return

    # 2 = INTRANS
    if conn.info.transaction_status == TransactionStatus(2):
        query = """
            DELETE FROM products
            WHERE id = ANY(%s) AND user_id = %s
            RETURNING 0 id
        """
        args = (product_ids, user_id)
        execute_db(query, args, conn)

        delete(user_id, product_list_id, conn)
    else:
        with conn.transaction():
            query = """
                DELETE FROM products
                WHERE id = ANY(%s) AND user_id = %s
                RETURNING 0 id
            """
            args = (product_ids, user_id)
            execute_db(query, args, conn)

            delete(user_id, product_list_id, conn)

    if not open_conn:
        put_conn(conn)
