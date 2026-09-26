import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, session, flash, json
from flask_login import login_required, current_user

from shopee_bot import utils
from shopee_bot.database import get_conn, put_conn, query_db, \
    posts, posts_medias, posts_products, medias, schedulers, products
from shopee_bot.database.schedulers import NETWORK_FUNC_MAP
from shopee_bot.web.forms.posts import PostForm
from shopee_bot.scheduler import add_job, remove_job, run_job
from shopee_bot.apis import llm
from shopee_bot.web.limiter import limiter

posts_bp = Blueprint("posts", __name__)


@posts_bp.post("/posts/generate-copy")
@login_required
@limiter.limit("10 per minute")
def generate_copy():
    body = request.get_json(silent=True) or {}
    product_id = body.get("product_id")
    persona = body.get("persona") or "casual"

    if product_id is None:
        return {"error": "product_id é obrigatório."}, 400

    product = products.get(current_user.id, int(product_id))
    if not product:
        return {"error": "Produto não encontrado."}, 404

    try:
        text = llm.generate_product_copy(product, persona)
    except Exception as e:
        return {"error": str(e)}, 400

    return {"text": text}, 200


@posts_bp.get("/posts")
@login_required
def index():
    count = posts.count(current_user.id)
    cursor, limit = utils.get_cursor_limit_from_args(request)

    result, next_cursor = posts.query_paginated(
        current_user.id,
        cursor,
        limit
    )

    return render_template(
        "posts/index.html",
        posts=json.dumps(result),
        count=count,
        limit=limit,
        cursor=cursor,
        next_cursor=next_cursor
    )


@posts_bp.get("/posts/pre-add")
@login_required
def pre_add():
    return render_template("posts/pre-form.html")


@posts_bp.get("/posts/add")
@login_required
def add():
    product_ids = request.args.get("product-ids", [])
    if product_ids and type(product_ids) is str:
        try:
            product_ids = [int(id) for id in product_ids.split(',') if id.strip().isdigit()]
        except ValueError:
            product_ids = []

    return render_template(
        "posts/form.html",
        operation="add",
        product_ids=product_ids,
        form=session.pop("form", None)
    )


@posts_bp.get("/posts/<id>")
@login_required
def edit(id):
    result = posts.get(current_user.id, id)

    return render_template(
        "posts/form.html",
        operation="edit",
        posts=result,
        form=session.pop("form", None)
    )


@posts_bp.post("/posts/<id>")
@login_required
def run(id):
    job = schedulers.get_by_post_id(current_user.id, id)
    run_job(str(job["id"]))
    flash("Postagem em andamento", "success")
    return {}, 201


@posts_bp.post("/posts")
@login_required
def add_save():
    form = PostForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    conn = get_conn()
    with conn.transaction():
        parent_id = None
        head_post_id = None

        for index, post in enumerate(form.posts.data):
            post_data = {
                "text": post["text"],
                "post_id": parent_id
            }
            if index == 0:
                post_data["network"] = form.network.data
            post_id = posts.insert(current_user.id, post_data, conn)
            parent_id = post_id

            if index == 0:
                head_post_id = post_id

            for f_index, file in enumerate(form.files.data[index]):
                if file is None:
                    continue

                filename = secure_filename(file.filename)
                file_path = os.path.join(f"web/media/{post_id}", filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

                media_id = medias.insert(
                    current_user.id,
                    {
                        "file_name": filename,
                        "file_path": file_path,
                        "size": os.stat(file_path).st_size,
                        "type": medias.MediaType.IMAGE
                        if "image" in file.mimetype
                        else medias.MediaType.VIDEO
                    },
                    conn
                )

                posts_medias.insert(
                    {
                        "post_id": post_id,
                        "media_id": media_id,
                        "display_order": f_index
                    },
                    conn
                )

        for p_index, product_id in enumerate(form.product_ids.data):
            posts_products.insert(
                {
                    "post_id": head_post_id,
                    "product_id": product_id,
                    "display_order": p_index
                },
                conn
            )

        if form.job.data:
            job = {
                **form.job.data,
                # func vem da rede escolhida, não do que o cliente
                # mandar em job.func — evita depender do default 'bot_post'
                # fixo no JS (form-script.html) e destrava as outras redes.
                "func": NETWORK_FUNC_MAP.get(form.network.data, "bot_post"),
                "post_id": head_post_id,
            }
            add_job(current_user.id, job, conn)

    put_conn(conn)
    flash("Postagem criada", "success")
    return {}, 201


@posts_bp.put("/posts/<id>")
@login_required
def edit_save(id):
    form = PostForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    conn = get_conn()
    with conn.transaction():
        parent_id = None
        head_post_id = None
        medias_to_delete = list()

        for index, post in enumerate(form.posts.data):
            post_data = {
                "text": post["text"],
                "post_id": parent_id,
            }
            if index == 0:
                post_data["network"] = form.network.data

            post_id = None
            if "id" in post and post["id"] is not None:
                post_id = posts.update(
                    current_user.id, post["id"], post_data, conn
                )
            else:
                post_id = posts.insert(current_user.id, post_data, conn)

            parent_id = post_id

            if index == 0:
                head_post_id = post_id

            # save media's file_path from post
            media_ids = [
                media["id"] for media in list(
                    filter(lambda media: "id" in media, post["medias"])
                )
            ]
            if len(media_ids) > 0:
                file_paths = posts_medias.get_file_paths_diff(
                    post_id,
                    media_ids
                )
                if len(file_paths) > 0:
                    for file_path in file_paths:
                        medias_to_delete.append(file_path["file_path"])

                    # remove deleted medias from post
                    posts_medias.delete_media_diff(post_id, media_ids, conn)

            next_display_order = posts_medias.get_next_display_order(post_id)

            # upload medias
            for f_index, file in enumerate(form.files.data[index]):
                if file is None:
                    continue

                filename = secure_filename(file.filename)
                file_path = os.path.join(f"web/media/{post_id}", filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

                media_id = medias.insert(
                    current_user.id,
                    {
                        "file_name": filename,
                        "file_path": file_path,
                        "size": os.stat(file_path).st_size,
                        "type": medias.MediaType.IMAGE
                        if "image" in file.mimetype
                        else medias.MediaType.VIDEO
                    },
                    conn
                )

                posts_medias.insert(
                    {
                        "post_id": post_id,
                        "media_id": media_id,
                        "display_order": next_display_order + f_index
                    },
                    conn
                )

        # remove deleted product_ids from post
        posts_products.delete_product_diff(
            head_post_id,
            form.product_ids.data,
            conn
        )

        # associate new product_ids to post
        product_ids_display_order = query_db(
            """
                WITH next_display_order AS (
                    SELECT COALESCE(
                        MAX(display_order + 1), 0
                    ) AS next_display_order
                    FROM posts_products
                    WHERE post_id = %s
                )
                SELECT
                    array_agg(t.product_id) product_ids, n.next_display_order
                FROM unnest(%s::integer[]) AS t(product_id)
                CROSS JOIN next_display_order n
                LEFT JOIN posts_products pp
                    ON pp.product_id = t.product_id
                    AND pp.post_id = %s
                WHERE pp.product_id IS NULL
                GROUP BY n.next_display_order
            """,
            (head_post_id, form.product_ids.data, head_post_id),
            True
        )
        new_product_ids = list()
        next_display_order = 0
        if product_ids_display_order:
            new_product_ids = product_ids_display_order["product_ids"]
            next_display_order = product_ids_display_order[
                "next_display_order"
            ]

        for p_index, product_id in enumerate(new_product_ids):
            posts_products.insert(
                {
                    "post_id": head_post_id,
                    "product_id": product_id,
                    "display_order": next_display_order + p_index
                },
                conn
            )

        # remove old job and create a new one
        if form.job.data:
            job_id = form.job.data["id"]
            remove_job(current_user.id, job_id, conn)

            job = {
                **form.job.data,
                "func": NETWORK_FUNC_MAP.get(form.network.data, "bot_post"),
                "post_id": head_post_id,
            }
            add_job(current_user.id, job, conn)

        # remove deleted medias
        for file_path in medias_to_delete:
            os.remove(file_path)

    put_conn(conn)
    flash("Postagem atualizada", "success")
    return {}, 200


@posts_bp.delete("/posts/<id>")
@login_required
def delete(id):
    medias_to_delete = list()
    posts_data = posts.get_for_delete(current_user.id, id)

    conn = get_conn()
    with conn.transaction():
        # remove job
        remove_job(
            current_user.id,
            str(posts_data[0]["scheduler"]["id"]),
            conn
        )

        for post in posts_data:
            id = post["id"]
            for media in post["medias"]:
                medias_to_delete.append(media["file_path"])
            posts.delete(current_user.id, id, conn)

        # remove deleted medias
        for file_path in medias_to_delete:
            os.remove(file_path)

    put_conn(conn)
    flash("Post removido", "success")
    return {}, 200
