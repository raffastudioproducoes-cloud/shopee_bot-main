from shopee_bot.database import execute_db


def insert(product_list_product, open_conn=None):
    query = """
        INSERT INTO product_lists_products(product_list_id, product_id)
        VALUES(%s, %s)
        ON CONFLICT (product_list_id, product_id)
        DO UPDATE
            SET product_list_id=EXCLUDED.product_list_id
        RETURNING 0 id
    """
    args = (
        product_list_product["product_list_id"],
        product_list_product["product_id"]
    )
    return execute_db(query, args, open_conn)


def delete(product_list_id, product_id, open_conn=None):
    query = """
        DELETE FROM product_lists_products
        WHERE product_list_id = %s AND product_id = %s
    """
    args = (product_list_id, product_id)
    execute_db(query, args, open_conn)


def delete_not_in(product_list_id, product_ids, open_conn=None):
    query = """
        DELETE FROM product_lists_products
        WHERE product_list_id = %s AND product_id NOT IN (
            SELECT unnest(%s::integer[])
        )
        RETURNING 0 id
    """
    args = (product_list_id, product_ids)
    execute_db(query, args, open_conn)
