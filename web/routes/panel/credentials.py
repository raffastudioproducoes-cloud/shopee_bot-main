from flask import render_template, flash, redirect, \
    url_for, session
from flask_login import login_required, fresh_login_required, current_user
from shopee_bot.web.limiter import limiter

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
    # Forms state presets para cada rede (pré-preenche valores em caso de erro)
    x_form = session.pop("x_form", {}) or {}
    x_form_errors = session.pop("x_form_errors", {}) or {}
    facebook_form = session.pop("facebook_form", {}) or {}
    facebook_form_errors = session.pop("facebook_form_errors", {}) or {}
    instagram_form = session.pop("instagram_form", {}) or {}
    instagram_form_errors = session.pop("instagram_form_errors", {}) or {}
    tiktok_form = session.pop("tiktok_form", {}) or {}
    tiktok_form_errors = session.pop("tiktok_form_errors", {}) or {}
    kwai_form = session.pop("kwai_form", {}) or {}
    kwai_form_errors = session.pop("kwai_form_errors", {}) or {}

    shopee_form = session.pop("shopee_form", {}) or {}
    shopee_form_errors = session.pop("shopee_form_errors", {}) or {}
    threads_form = session.pop("threads_form", {}) or {}
    threads_form_errors = session.pop("threads_form_errors", {}) or {}

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
        form=session.pop("form", None),
        shopee_form=shopee_form,
        shopee_form_errors=shopee_form_errors,
        threads_form=threads_form,
        threads_form_errors=threads_form_errors,
        x_form=x_form,
        x_form_errors=x_form_errors,
        facebook_form=facebook_form,
        facebook_form_errors=facebook_form_errors,
        instagram_form=instagram_form,
        instagram_form_errors=instagram_form_errors,
        tiktok_form=tiktok_form,
        tiktok_form_errors=tiktok_form_errors,
        kwai_form=kwai_form,
        kwai_form_errors=kwai_form_errors,
    )


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_shopee_save(id):
    form = ShopeeForm()

    if not form.validate():
        session["shopee_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["shopee_form_errors"] = {
            "app_id": form.app_id.errors,
            "secret": form.secret.errors,
        }
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    _credential_id_str = str(id).strip() if id else ""
    try:
        if not ShopeeAPI.query_auth_validate(
            form.app_id.data,
            form.secret.data
        ):
            session["shopee_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["shopee_form_errors"] = {
                "app_id": ["Não foi possível validar a autenticação da Shopee"],
                "secret": ["Não foi possível validar a autenticação da Shopee"],
            }
            flash("Não foi possível validar a autenticação da Shopee", "error")
            return redirect(url_for("panel.credentials_index"))
    except Exception as e:
        # Log the error for debugging (in production, use proper logging)
        session["shopee_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["shopee_form_errors"] = {
            "app_id": ["Erro ao validar a autenticação da Shopee"],
            "secret": ["Erro ao validar a autenticação da Shopee"],
        }
        flash("Erro ao validar a autenticação da Shopee. Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))

    credential = {
        "app_id": form.app_id.data,
        "secret": form.secret.data,
        "status": True,
    }
    if id is None or _credential_id_str.lower() in ("none", "new") or _credential_id_str == "":
        try:
            shopee_credentials.insert(current_user.id, credential)
        except Exception as e:
            session["shopee_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["shopee_form_errors"] = {
                "app_id": ["Erro ao salvar a autenticação da Shopee"],
                "secret": ["Erro ao salvar a autenticação da Shopee"],
            }
            flash("Erro ao salvar a autenticação da Shopee. Tente novamente mais tarde.", "error")
            return redirect(url_for("panel.credentials_index"))
    else:
        try:
            shopee_credentials.update(current_user.id, id, credential)
        except Exception as e:
            session["shopee_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["shopee_form_errors"] = {
                "app_id": ["Erro ao atualizar a autenticação da Shopee"],
                "secret": ["Erro ao atualizar a autenticação da Shopee"],
            }
            flash("Erro ao atualizar a autenticação da Shopee. Tente novamente mais tarde.", "error")
            return redirect(url_for("panel.credentials_index"))

    session.pop("shopee_form", None)
    session.pop("shopee_form_errors", None)
    flash("Autenticação da Shopee atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_shopee_del(id):
    try:
        shopee_credentials.update(
            current_user.id,
            id,
            {
                "app_id": None,
                "secret": None,
                "status": False
            }
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação da Shopee ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    flash("Autenticação da Shopee removida", "success")
    return {}, 200


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_threads_save(id):
    # O parâmetro <id> na URL é o user_id (vem de current_user.id no
    # template), NÃO o id da credencial. Buscamos o id real da
    # credencial do Threads para este usuário.
    from shopee_bot.database import users as _users
    _cred = _users.get_credentials(current_user.id)
    credential_id = _cred.get("threads_id")

    # O OAuth do Threads redireciona de VOLTA com GET ?code=... (ou
    # ?error=...), não via POST de formulário. Aceitamos ambos:
    # GET (retorno do Meta) e POST (fluxo manual, se houver).
    # Além disso, aceitamos um token de testador colado manualmente
    # (campo "token") — útil quando o app ainda não publicou ou o
    # callback do Meta não salva. Nesse caso buscamos o user_id via API.
    from flask import request as _request

    code = _request.args.get("code") or _request.form.get("code")
    error = _request.args.get("error")
    token = _request.form.get("token")

    if error:
        flash(f"Threads: {error}", "error")
        return redirect(url_for("panel.credentials_index"))

    if not code and not token:
        form = ThreadsForm()
        if not form.validate():
            session["threads_form"] = {
                "code": form.code.data or "",
                "token": form.token.data or "",
            }
            session["threads_form_errors"] = {
                "code": form.code.errors,
                "token": form.token.errors,
            }
            flash("Erro(s) de validação", "error")
            return redirect(url_for("panel.credentials_index"))
        flash("Informe o código do OAuth ou um token de acesso", "error")
        session["threads_form"] = {
            "code": form.code.data or "",
            "token": form.token.data or "",
        }
        return redirect(url_for("panel.credentials_index"))

    if token:
        # Token de testador colado manualmente: busca o user_id da conta
        try:
            t_user_id = ThreadsAPI.get_user_id(token)
        except Exception as e:
            session["threads_form"] = {
                "code": code or "",
                "token": token or "",
            }
            session["threads_form_errors"] = {
                "code": [],
                "token": [f"Threads: falha ao validar token ({e})"],
            }
            flash(f"Threads: falha ao validar token ({e})", "error")
            return redirect(url_for("panel.credentials_index"))
        access_token = token
    else:
        try:
            t_user_id, access_token = ThreadsAPI.get_user_auth_id_token(
                code
            )
        except Exception as e:
            session["threads_form"] = {
                "code": code or "",
                "token": token or "",
            }
            session["threads_form_errors"] = {
                "code": [],
                "token": [f"Threads: falha no OAuth ({e})"],
            }
            flash(f"Threads: falha no OAuth ({e})", "error")
            return redirect(url_for("panel.credentials_index"))

    credential = {
        "t_user_id": t_user_id,
        "access_token": access_token,
        "status": True,
    }
    try:
        if credential_id is None:
            threads_credentials.insert(current_user.id, credential)
        else:
            threads_credentials.update(current_user.id, credential_id, credential)
    except Exception as e:
        session["threads_form"] = {
            "code": code or "",
            "token": token or "",
        }
        session["threads_form_errors"] = {
            "code": [],
            "token": [f"Erro ao salvar a autenticação do Threads ({type(e).__name__})"],
        }
        flash("Erro ao salvar a autenticação do Threads. Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    session.pop("threads_form", None)
    session.pop("threads_form_errors", None)
    flash("Autenticação do Threads atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_threads_del(id):
    try:
        threads_credentials.update(
            current_user.id,
            id,
            {
                "t_user_id": None,
                "access_token": None,
                "status": False,
            },
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação do Threads ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
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
@limiter.limit("10 per minute")
def credentials_x_save(id):
    form = XForm()

    if not form.validate():
        session["x_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["x_form_errors"] = {
            "app_id": form.app_id.errors,
            "secret": form.secret.errors,
        }
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    _credential_id_str = str(id).strip() if id else ""
    if id is None or _credential_id_str.lower() in ("none", "new") or _credential_id_str == "":
        try:
            x_credentials.insert(current_user.id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        except Exception as e:
            session["x_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["x_form_errors"] = {
                "app_id": ["Erro ao salvar a autenticação do X"],
                "secret": ["Erro ao salvar a autenticação do X"],
            }
            flash("Erro ao salvar a autenticação do X. Tente novamente mais tarde.", "error")
            return redirect(url_for("panel.credentials_index"))
    else:
        try:
            x_credentials.update(current_user.id, id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        except Exception as e:
            session["x_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["x_form_errors"] = {
                "app_id": ["Erro ao atualizar a autenticação do X"],
                "secret": ["Erro ao atualizar a autenticação do X"],
            }
            flash("Erro ao atualizar a autenticação do X. Tente novamente mais tarde.", "error")
            return redirect(url_for("panel.credentials_index"))

    session.pop("x_form", None)
    session.pop("x_form_errors", None)
    flash("Autenticação do X atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_x_del(id):
    try:
        x_credentials.update(
            current_user.id,
            id,
            {
                "app_id": None,
                "secret": None,
                "status": False
            }
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação do X ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    flash("Autenticação do X removida", "success")
    return {}, 200


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_facebook_save(id):
    form = FacebookForm()

    if not form.validate():
        session["facebook_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["facebook_form_errors"] = {
            "app_id": form.app_id.errors,
            "secret": form.secret.errors,
        }
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    _credential_id_str = str(id).strip() if id else ""
    if id is None or _credential_id_str.lower() in ("none", "new") or _credential_id_str == "":
        try:
            facebook_credentials.insert(current_user.id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        except Exception as e:
            session["facebook_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["facebook_form_errors"] = {
                "app_id": ["Erro ao salvar a autenticação do Facebook"],
                "secret": ["Erro ao salvar a autenticação do Facebook"],
            }
            flash("Erro ao salvar a autenticação do Facebook. Tente novamente mais tarde.", "error")
            return redirect(url_for("panel.credentials_index"))
    else:
        try:
            facebook_credentials.update(current_user.id, id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        except Exception as e:
            session["facebook_form"] = {
                "app_id": form.app_id.data or "",
                "secret": form.secret.data or "",
            }
            session["facebook_form_errors"] = {
                "app_id": ["Erro ao atualizar a autenticação do Facebook"],
                "secret": ["Erro ao atualizar a autenticação do Facebook"],
            }
            flash("Erro ao atualizar a autenticação do Facebook. Tente novamente mais tarde.", "error")
            return redirect(url_for("panel.credentials_index"))

    session.pop("facebook_form", None)
    session.pop("facebook_form_errors", None)
    flash("Autenticação do Facebook atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_facebook_del(id):
    try:
        facebook_credentials.update(
            current_user.id,
            id,
            {
                "app_id": None,
                "secret": None,
                "status": False
            }
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação do Facebook ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    flash("Autenticação do Facebook removida", "success")
    return {}, 200


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_instagram_save(id):
    form = InstagramForm()

    if not form.validate():
        session["form"] = {"instagram": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    _credential_id_str = str(id).strip() if id else ""
    try:
        if id is None or _credential_id_str.lower() in ("none", "new") or _credential_id_str == "":
            instagram_credentials.insert(current_user.id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        else:
            instagram_credentials.update(current_user.id, id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
    except Exception as e:
        session["instagram_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["instagram_form_errors"] = {
            "app_id": [f"Erro ao salvar a autenticação do Instagram ({type(e).__name__})"],
            "secret": [f"Erro ao salvar a autenticação do Instagram ({type(e).__name__})"],
        }
        flash("Erro ao salvar a autenticação do Instagram. Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    session.pop("instagram_form", None)
    session.pop("instagram_form_errors", None)
    flash("Autenticação do Instagram atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_instagram_del(id):
    try:
        instagram_credentials.update(
            current_user.id,
            id,
            {
                "app_id": None,
                "secret": None,
                "status": False
            }
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação do Instagram ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    flash("Autenticação do Instagram removida", "success")
    return {}, 200


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_tiktok_save(id):
    form = TiktokForm()

    if not form.validate():
        session["form"] = {"tiktok": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    _credential_id_str = str(id).strip() if id else ""
    try:
        if id is None or _credential_id_str.lower() in ("none", "new") or _credential_id_str == "":
            tiktok_credentials.insert(current_user.id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        else:
            tiktok_credentials.update(current_user.id, id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
    except Exception as e:
        session["tiktok_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["tiktok_form_errors"] = {
            "app_id": [f"Erro ao salvar a autenticação do TikTok ({type(e).__name__})"],
            "secret": [f"Erro ao salvar a autenticação do TikTok ({type(e).__name__})"],
        }
        flash("Erro ao salvar a autenticação do TikTok. Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    session.pop("tiktok_form", None)
    session.pop("tiktok_form_errors", None)
    flash("Autenticação do TikTok atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_tiktok_del(id):
    try:
        tiktok_credentials.update(
            current_user.id,
            id,
            {
                "app_id": None,
                "secret": None,
                "status": False
            }
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação do TikTok ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    flash("Autenticação do TikTok removida", "success")
    return {}, 200


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_kwai_save(id):
    form = KwaiForm()

    if not form.validate():
        session["form"] = {"kwai": form.errors}
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.credentials_index"))

    _credential_id_str = str(id).strip() if id else ""
    try:
        if id is None or _credential_id_str.lower() in ("none", "new") or _credential_id_str == "":
            kwai_credentials.insert(current_user.id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
        else:
            kwai_credentials.update(current_user.id, id, {
                "app_id": form.app_id.data,
                "secret": form.secret.data,
                "status": True,
            })
    except Exception as e:
        session["kwai_form"] = {
            "app_id": form.app_id.data or "",
            "secret": form.secret.data or "",
        }
        session["kwai_form_errors"] = {
            "app_id": [f"Erro ao salvar a autenticação do Kwai ({type(e).__name__})"],
            "secret": [f"Erro ao salvar a autenticação do Kwai ({type(e).__name__})"],
        }
        flash("Erro ao salvar a autenticação do Kwai. Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    session.pop("kwai_form", None)
    session.pop("kwai_form_errors", None)
    flash("Autenticação do Kwai atualizada", "success")
    return redirect(url_for("panel.credentials_index"))


@fresh_login_required
@login_required
@limiter.limit("10 per minute")
def credentials_kwai_del(id):
    try:
        kwai_credentials.update(
            current_user.id,
            id,
            {
                "app_id": None,
                "secret": None,
                "status": False
            }
        )
    except Exception as e:
        flash(f"Erro ao remover a autenticação do Kwai ({type(e).__name__}). Tente novamente mais tarde.", "error")
        return redirect(url_for("panel.credentials_index"))
    flash("Autenticação do Kwai removida", "success")
    return {}, 200