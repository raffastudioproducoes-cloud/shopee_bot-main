import os
from flask import Blueprint, redirect
from shopee_bot.clogging import logger
from shopee_bot.database import get_conn, put_conn, users, \
    shopee_credentials, threads_credentials, \
    x_credentials, facebook_credentials, instagram_credentials, \
    tiktok_credentials, kwai_credentials

startup_bp = Blueprint("startup", __name__, url_prefix="/startup")


@startup_bp.get("")
def index():
    # Bootstrap do admin inicial só existe se o operador definir a senha
    # via env (STARTUP_ADMIN_PASSWORD). Antes a senha era aleatória e ia
    # pro log em texto puro, e qualquer um podia disparar a rota sem login.
    admin_password = os.environ.get("STARTUP_ADMIN_PASSWORD")
    if not admin_password:
        # return direto, não abort(): o errorhandler(Exception) global
        # (web/__init__.py) transformaria o 404 em 500.
        return {"error": "Não encontrado"}, 404

    count = users.count()

    if count != 0:
        # "/" em vez de url_for("index"): endpoint "index" só existe com
        # LEGACY_PANEL_ENABLED=true (ver web/__init__.py)
        return redirect("/")

    conn = get_conn()
    with conn.transaction():
        user_id = users.insert(
            {
                "username": "spoler",
                "password": admin_password,
                "access": "ADMIN"
            },
            conn
        )

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
    logger.warning(
        "Usuario admin inicial criado (username=spoler). Troque a senha e "
        "remova STARTUP_ADMIN_PASSWORD do ambiente."
    )
    return redirect("/")
