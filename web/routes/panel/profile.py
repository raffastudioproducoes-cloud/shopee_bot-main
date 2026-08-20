import bcrypt
from flask import render_template, flash, redirect, url_for, session
from flask_login import login_required, fresh_login_required, current_user

from shopee_bot.database import users
from shopee_bot.web.forms.panel import NewPasswordForm


@fresh_login_required
@login_required
def profile_index():
    user = users.get(current_user.id)

    return render_template(
        "panel/profile.html",
        user=user,
        # be aware it's only form.errors dict
        form=session.pop("form", None)
    )


@fresh_login_required
@login_required
def profile_new_password():
    form = NewPasswordForm()

    if not form.validate():
        session["form"] = form.errors
        flash("Erro(s) de validação", "error")
        return redirect(url_for("panel.profile_index"))

    user = users.get_by_username(current_user.username)

    if not bcrypt.checkpw(
        form.current_password.data.encode("ascii"),
        user["password"].encode("ascii")
    ):
        # @TODO criar error para mostar embaixo do input
        # session["form"] = form.errors
        flash("Senha atual incorreta", "error")
        return redirect(url_for("panel.profile_index"))

    users.update_password(
        current_user.id,
        form.new_password.data
    )
    flash("Senha atualizada", "success")
    return redirect(url_for("panel.profile_index"))
