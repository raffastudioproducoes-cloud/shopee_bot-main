from flask import Blueprint, redirect, url_for
from shopee_bot.database import get_conn, put_conn, users, \
    shopee_credentials, threads_credentials

startup_bp = Blueprint("startup", __name__, url_prefix="/startup")


@startup_bp.get("")
def index():
    count = users.count()

    if count != 0:
        return redirect(url_for("index"))

    conn = get_conn()
    with conn.transaction():
        user_id = users.insert(
            {
                "username": "spoler",
                "password": "12345678",
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

    put_conn(conn)
    return redirect(url_for("index"))
