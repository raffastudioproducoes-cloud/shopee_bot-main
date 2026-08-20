import re
from flask import Blueprint, render_template, request, flash, redirect, \
    url_for, jsonify, json, session
from flask_login import login_required, current_user

from shopee_bot.web.helpers import is_url_for
from shopee_bot import utils
from shopee_bot.database import products, shopee_credentials
from shopee_bot.apis import shopee as ShopeeAPI
from shopee_bot.web.forms.products import ProductForm

products_bp = Blueprint("products", __name__)


@products_bp.get("/products")
@login_required
def index():
    count = products.count(current_user.id)
    cursor, limit = utils.get_cursor_limit_from_args(request)

    result, next_cursor = products.query_paginated(
        current_user.id,
        cursor,
        limit
    )

    return render_template(
        "products/index.html",
        products=json.dumps(result),
        count=count,
        limit=limit,
        cursor=cursor,
        next_cursor=next_cursor,
    )


@products_bp.get("/products.json")
@login_required
def index_json():
    cursor, limit = utils.get_cursor_limit_from_args(request)
    ids = request.args.get('ids', None)

    if ids:
        ids = [int(id) for id in ids.split(',')]
        count = products.count_by_id(current_user.id, ids)

        result, next_cursor = products.query_paginated_by_id(
            current_user.id,
            cursor,
            limit,
            ids
        )
    else:
        count = products.count(current_user.id)
        order_by_ids = request.args.get("order-by-ids", None)

        if order_by_ids:
            order_by_ids = [int(id) for id in order_by_ids.split(",")]
            result, next_cursor = products.query_paginated_order_by_id(
                current_user.id,
                cursor,
                limit,
                order_by_ids
            )
        else:
            result, next_cursor = products.query_paginated(
                current_user.id,
                cursor,
                limit
            )

    return jsonify({
        "products": result,
        "count": count,
        "limit": limit,
        "cursor": cursor,
        "next-cursor": next_cursor
    })


@products_bp.get("/products/add")
@login_required
def add():
    product_url = request.args.get("product_url")
    re_result = re.findall(r"\d{5,}", product_url)

    # validate URL
    if not is_url_for(product_url, "https://shopee.com.br") \
            or not re_result or len(re_result) < 2:
        flash(
            "Por favor, utilize uma URL válida da Shopee",
            "error"
        )
        return redirect(url_for("products.index"))

    user_data = shopee_credentials.get_by_user_id(current_user.id)
    app_id = user_data["shopee_app_id"]
    secret = user_data["shopee_secret"]
    status = user_data["shopee_status"]

    if not app_id or not secret or status is False:
        flash(
            "Cadastre uma chave da Shopee válida antes de prosseguir",
            "error"
        )
        return redirect(url_for("products.index"))

    # get product
    product = ShopeeAPI.query_product(app_id, secret, product_url)
    return render_template(
        "products/form.html",
        product=product,
        operation="add",
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@products_bp.get("/products/<id>")
@login_required
def edit(id):
    result = products.get(current_user.id, id)

    return render_template(
        "products/form.html",
        product=result,
        operation="edit",
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@products_bp.post("/products")
@login_required
def add_save():
    form = ProductForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    products.insert(current_user.id, form.data)
    flash("Produto criado", "success")
    return {}, 201


@products_bp.put("/products/<id>/update")
@login_required
def products_update(id):
    user_data = shopee_credentials.get_by_user_id(current_user.id)
    app_id = user_data["shopee_app_id"]
    secret = user_data["shopee_secret"]
    status = user_data["shopee_status"]

    if not app_id or not secret or status is False:
        flash(
            "Cadastre uma chave da Shopee válida antes de prosseguir",
            "error"
        )
        return {}, 400

    product = products.get(current_user.id, id)
    updated_product = ShopeeAPI.query_product(
        app_id, secret, product["original_link"]
    )

    products.update(current_user.id, id, updated_product)
    flash("Produto atualizado", "success")
    return {}, 200


@products_bp.put("/products/<id>")
@login_required
def products_edit_save(id):
    form = ProductForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    products.update(current_user.id, id, form.data)
    flash("Produto atualizado", "success")
    return {}, 200


@products_bp.delete("/products/<id>")
@login_required
def products_del(id):
    products.delete(current_user.id, id)
    flash("Produto removido", "success")
    return {}, 200
