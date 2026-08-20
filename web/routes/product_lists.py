from flask import Blueprint, request, render_template, flash, session, \
    jsonify, json
from flask_login import login_required, current_user

from shopee_bot import utils
from shopee_bot.database import product_lists, product_lists_products, \
    get_conn, put_conn, query_db
from shopee_bot.web.forms.product_lists import ProductListForm

product_lists_bp = Blueprint("product_lists", __name__)


@product_lists_bp.get("/product-lists")
@login_required
def index():
    count = product_lists.count(current_user.id)
    cursor, limit = utils.get_cursor_limit_from_args(request)

    result, next_cursor = product_lists.query_paginated(
        current_user.id,
        cursor,
        limit,
    )

    return render_template(
        "product-lists/index.html",
        product_lists=json.dumps(result),
        count=count,
        cursor=cursor,
        limit=limit,
        next_cursor=next_cursor,
    )


@product_lists_bp.get("/product-lists.json")
@login_required
def index_json():
    cursor, limit = utils.get_cursor_limit_from_args(request)
    ids = request.args.get("ids", None)
    if ids:
        ids = [int(id) for id in ids.split(",")]

        count_query = """
            SELECT COUNT(*)
            FROM product_lists
            WHERE user_id = %s AND id = ANY(%s)
        """
        count = query_db(count_query, (current_user.id, ids), True)["count"]

        result, next_cursor = product_lists.query_paginated_by_id(
            current_user.id,
            cursor,
            limit,
            ids
        )
    else:
        count = product_lists.count(current_user.id)

        result, next_cursor = product_lists.query_paginated(
            current_user.id,
            cursor,
            limit,
        )

    return jsonify({
        "product_lists": result,
        "count": count,
        "limit": limit,
        "cursor": cursor,
        "next_cursor": next_cursor
    })


@product_lists_bp.get("/product-lists/add")
@login_required
def add():
    return render_template(
        "product-lists/form.html",
        operation="add",
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@product_lists_bp.get("/product-lists/<id>")
@login_required
def edit(id):
    result = product_lists.get(current_user.id, id)

    return render_template(
        "product-lists/form.html",
        product_list=result,
        operation="edit",
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@product_lists_bp.post("/product-lists")
@login_required
def add_save():
    form = ProductListForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    conn = get_conn()
    with conn.transaction():
        product_list_id = product_lists.insert(
            current_user.id, form.data, conn
        )
        for product_id in form.list.data:
            product_lists_products.insert(
                {
                    "product_list_id": product_list_id,
                    "product_id": product_id
                },
                conn
            )

    put_conn(conn)
    flash("Lista de produtos criada", "success")
    return {}, 201


@product_lists_bp.put("/product-lists/<id>")
@login_required
def edit_save(id):
    form = ProductListForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    conn = get_conn()
    with conn.transaction():
        product_lists_products.delete_not_in(id, form.list.data, conn)
        product_lists.update(current_user.id, id, form.data, conn)

        for product_id in form.list.data:
            product_lists_products.insert(
                {
                    "product_list_id": id,
                    "product_id": product_id
                },
                conn
            )

    put_conn(conn)
    flash("Lista de produtos atualizada", "success")
    return {}, 200


@product_lists_bp.delete("/product-lists/<id>")
@login_required
def delete(id):
    with_products = request.args.get("with-products", default=False, type=bool)
    if with_products:
        product_lists.delete_with_products(current_user.id, id)
    else:
        product_lists.delete(current_user.id, id)
    flash("Lista de produtos removida", "success")
    return {}, 200
