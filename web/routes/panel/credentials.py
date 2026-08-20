from flask import render_template, flash, redirect, \
    url_for, session
from flask_login import login_required, fresh_login_required, current_user

from shopee_bot.database import users, shopee_credentials, threads_credentials
from shopee_bot.web.forms.panel import ShopeeForm, ThreadsForm
from shopee_bot.apis import shopee as ShopeeAPI, threads as ThreadsAPI


@fresh_login_required
@login_required
def credentials_index():
    user_data = users.get_credentials(current_user.id)
    shopee = {
        "id": user_data["shopee_id"],
        "app_id": user_data["shopee_app_id"] or "",
        "secret": user_data["shopee_secret"] or "",
        "status": user_data["shopee_status"]
    }
    threads = {
        "id": user_data["threads_id"],
        "user_id": user_data["threads_user_id"] or "",
        "access_token": user_data["threads_access_token"] or "",
        "status": user_data["threads_status"]
    }

    return render_template(
        "panel/credentials.html",
        shopee=shopee,
        threads=threads,
        threads_user_auth_url=ThreadsAPI.get_user_auth_url(),
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@fresh_login_required
@login_required
def credentials_shopee_save(id):
    form = ShopeeForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    if not ShopeeAPI.query_auth_validate(
        form.app_id.data,
        form.secret.data
    ):
        flash(
            "Não foi possível validar a autenticação da Shopee",
            "error"
        )
        return redirect(url_for("panel.credentials_index"))

    shopee_credentials.update(
        current_user.id,
        id,
        {
            "app_id": form.app_id.data,
            "secret": form.secret.data,
            "status": True,
        }
    )
    flash("Autenticação da Shopee atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_shopee_del(id):
    shopee_credentials.update(
        current_user.id,
        id,
        {
            "app_id": None,
            "secret": None,
            "status": False
        }
    )
    flash("Autenticação da Shopee removida", "success")
    return {}, 200


@fresh_login_required
@login_required
def credentials_threads_save(id):
    form = ThreadsForm()

    if not form.validate():
        session["form"] = {"threads": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    t_user_id, access_token = ThreadsAPI.get_user_auth_id_token(
        form.code.data
    )

    threads_credentials.update(
        current_user.id,
        id,
        {
            "t_user_id": t_user_id,
            "access_token": access_token,
            "status": True
        },
    )
    flash("Autenticação do Threads atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_threads_del(id):
    threads_credentials.update(
        current_user.id,
        id,
        {
            "t_user_id": None,
            "access_token": None,
            "status": False,
        },
    )

    flash("Token de acesso do Threads removido", "success")
    return {}, 200
