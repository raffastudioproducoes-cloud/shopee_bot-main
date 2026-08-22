from flask import Blueprint, request, render_template, redirect, \
    url_for, flash, session, json
from flask_login import login_required, current_user

from shopee_bot import utils
from shopee_bot.database import get_conn, put_conn, users, \
    schedulers, shopee_credentials, threads_credentials, \
    x_credentials, facebook_credentials, instagram_credentials, \
    tiktok_credentials, kwai_credentials
from shopee_bot.scheduler import remove_job
from shopee_bot.web.forms.users import UserAddForm, UserEditForm

users_bp = Blueprint("users", __name__)


@users_bp.before_request
def before_request():
    if current_user.access != "ADMIN":
        flash("Você não tem acesso a esta página.", "error")
        return redirect(url_for("index"))


@users_bp.get("/users")
@login_required
def index():
    count = users.count()
    cursor, limit = utils.get_cursor_limit_from_args(request)

    result, next_cursor = users.query_paginated(
        cursor,
        limit
    )

    return render_template(
        "users/index.html",
        users=json.dumps(result),
        count=count,
        limit=limit,
        cursor=cursor,
        next_cursor=next_cursor
    )


@users_bp.get("/users/add")
@login_required
def add():
    return render_template(
        "users/form.html",
        operation="add",
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@users_bp.get("/users/<id>")
@login_required
def edit_view(id):
    result = users.get(id)

    return render_template(
        "users/form.html",
        user=result,
        operation="edit",
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@users_bp.post("/users")
@login_required
def save():
    form = UserAddForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    conn = get_conn()
    with conn.transaction():
        user_id = users.insert(form.data, conn)

        shopee_credentials.insert(
            user_id,
            {
                "app_id": None,
                "secret": None,
                "status": False,
            },
            conn
        )

        threads_credentials.insert(
            user_id,
            {
                "t_user_id": None,
                "access_token": None,
                "status": False,
            },
            conn
        )

        for credentials_module in (
            x_credentials,
            facebook_credentials,
            instagram_credentials,
            tiktok_credentials,
            kwai_credentials,
        ):
            credentials_module.insert(
                user_id,
                {
                    "app_id": None,
                    "secret": None,
                    "status": False,
                },
                conn
            )

    put_conn(conn)
    flash("Usuário criado", "success")
    return {}, 201


@users_bp.put("/users/<id>")
@login_required
def edit_save(id):
    form = UserEditForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return {}, 400

    users.update(id, form.data)
    flash("Usuário atualizado", "success")
    return {}, 200


@users_bp.delete("/users/<id>")
@login_required
def delete(id):
    conn = get_conn()
    with conn.transaction():
        for job in schedulers.query(id):
            job_id = job.id
            remove_job(id, job_id, conn)

        users.delete(id, conn)
    put_conn(conn)
    flash("Usuário removido", "success")
    return {}, 200
