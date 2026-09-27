import bcrypt
from flask import Blueprint, abort, redirect, render_template, request, \
    flash
from flask_login import login_required, login_user, logout_user

from shopee_bot.database import users
from shopee_bot.web.user import User
from shopee_bot.web.forms.auth import LoginForm
from shopee_bot.web.helpers import is_safe_url
from shopee_bot.web.limiter import limiter

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/auth/login")
def login_get():
    return render_template("auth/index.html")


@auth_bp.post("/auth/login")
@limiter.limit("5 per minute")
def login_post():
    next = request.form["next"]
    if next and not is_safe_url(next):
        return abort(400)

    form = LoginForm()

    if not form.validate():
        flash("Erro(s) de validação", "error")
        return render_template("auth/index.html", form=form), 400

    user = users.get_by_username(form.username.data)

    if not user or not bcrypt.checkpw(
        form.password.data.encode("ascii"),
        user["password"].encode("ascii")
    ):
        flash("Usuário ou senha inválidos", "error")
        return render_template("auth/index.html"), 400

    login_user(
        User(user["id"], user["username"], user["access"]),
        remember=True
    )

    flash("Logado", "success")
    # "/" em vez de url_for("index"): o endpoint "index" só existe com
    # LEGACY_PANEL_ENABLED=true (ver web/__init__.py) — "/" sempre resolve,
    # seja pro Jinja legado ou pro catch-all do SPA React
    return redirect(next or "/")


@auth_bp.get("/auth/logout")
@login_required
def logout_view():
    logout_user()
    flash("Você saiu da sessão", "success")
    return redirect("/")
