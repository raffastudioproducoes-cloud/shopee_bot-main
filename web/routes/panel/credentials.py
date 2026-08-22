from flask import render_template, flash, redirect, \
    url_for, session
from flask_login import login_required, fresh_login_required, current_user

from shopee_bot.database import users, shopee_credentials, \
    threads_credentials, x_credentials, facebook_credentials, \
    instagram_credentials, tiktok_credentials, kwai_credentials
from shopee_bot.web.forms.panel import ShopeeForm, ThreadsForm, XForm, \
    FacebookForm, InstagramForm, TiktokForm, KwaiForm
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
    x = {
        "id": user_data["x_id"],
        "app_id": user_data["x_app_id"] or "",
        "secret": user_data["x_secret"] or "",
        "status": user_data["x_status"]
    }
    facebook = {
        "id": user_data["facebook_id"],
        "app_id": user_data["facebook_app_id"] or "",
        "secret": user_data["facebook_secret"] or "",
        "status": user_data["facebook_status"]
    }
    instagram = {
        "id": user_data["instagram_id"],
        "app_id": user_data["instagram_app_id"] or "",
        "secret": user_data["instagram_secret"] or "",
        "status": user_data["instagram_status"]
    }
    tiktok = {
        "id": user_data["tiktok_id"],
        "app_id": user_data["tiktok_app_id"] or "",
        "secret": user_data["tiktok_secret"] or "",
        "status": user_data["tiktok_status"]
    }
    kwai = {
        "id": user_data["kwai_id"],
        "app_id": user_data["kwai_app_id"] or "",
        "secret": user_data["kwai_secret"] or "",
        "status": user_data["kwai_status"]
    }

    return render_template(
        "panel/credentials.html",
        shopee=shopee,
        threads=threads,
        x=x,
        facebook=facebook,
        instagram=instagram,
        tiktok=tiktok,
        kwai=kwai,
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


# X, Facebook, Instagram, TikTok e Kwai ainda não têm wrapper de API
# próprio (ver apis/threads.py e apis/shopee.py para o padrão a seguir).
# Por enquanto essas rotas só guardam app_id/secret cifrados e marcam
# status=True — sem validar contra a API real da rede. Plugar a
# validação (tipo ShopeeAPI.query_auth_validate) quando o wrapper de
# cada rede for implementado.

@fresh_login_required
@login_required
def credentials_x_save(id):
    form = XForm()

    if not form.validate():
        session["form"] = {"x": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    x_credentials.update(
        current_user.id,
        id,
        {
            "app_id": form.app_id.data,
            "secret": form.secret.data,
            "status": True,
        }
    )
    flash("Autenticação do X atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_x_del(id):
    x_credentials.update(
        current_user.id,
        id,
        {
            "app_id": None,
            "secret": None,
            "status": False
        }
    )
    flash("Autenticação do X removida", "success")
    return {}, 200


@fresh_login_required
@login_required
def credentials_facebook_save(id):
    form = FacebookForm()

    if not form.validate():
        session["form"] = {"facebook": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    facebook_credentials.update(
        current_user.id,
        id,
        {
            "app_id": form.app_id.data,
            "secret": form.secret.data,
            "status": True,
        }
    )
    flash("Autenticação do Facebook atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_facebook_del(id):
    facebook_credentials.update(
        current_user.id,
        id,
        {
            "app_id": None,
            "secret": None,
            "status": False
        }
    )
    flash("Autenticação do Facebook removida", "success")
    return {}, 200


@fresh_login_required
@login_required
def credentials_instagram_save(id):
    form = InstagramForm()

    if not form.validate():
        session["form"] = {"instagram": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    instagram_credentials.update(
        current_user.id,
        id,
        {
            "app_id": form.app_id.data,
            "secret": form.secret.data,
            "status": True,
        }
    )
    flash("Autenticação do Instagram atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_instagram_del(id):
    instagram_credentials.update(
        current_user.id,
        id,
        {
            "app_id": None,
            "secret": None,
            "status": False
        }
    )
    flash("Autenticação do Instagram removida", "success")
    return {}, 200


@fresh_login_required
@login_required
def credentials_tiktok_save(id):
    form = TiktokForm()

    if not form.validate():
        session["form"] = {"tiktok": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    tiktok_credentials.update(
        current_user.id,
        id,
        {
            "app_id": form.app_id.data,
            "secret": form.secret.data,
            "status": True,
        }
    )
    flash("Autenticação do TikTok atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_tiktok_del(id):
    tiktok_credentials.update(
        current_user.id,
        id,
        {
            "app_id": None,
            "secret": None,
            "status": False
        }
    )
    flash("Autenticação do TikTok removida", "success")
    return {}, 200


@fresh_login_required
@login_required
def credentials_kwai_save(id):
    form = KwaiForm()

    if not form.validate():
        session["form"] = {"kwai": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    kwai_credentials.update(
        current_user.id,
        id,
        {
            "app_id": form.app_id.data,
            "secret": form.secret.data,
            "status": True,
        }
    )
    flash("Autenticação do Kwai atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
def credentials_kwai_del(id):
    kwai_credentials.update(
        current_user.id,
        id,
        {
            "app_id": None,
            "secret": None,
            "status": False
        }
    )
    flash("Autenticação do Kwai removida", "success")
    return {}, 200
