from flask import Blueprint

from shopee_bot.web.routes.panel.profile import profile_index, \
    profile_new_password
from shopee_bot.web.routes.panel.credentials import credentials_index, \
    credentials_shopee_save, credentials_shopee_del, \
    credentials_threads_save, credentials_threads_del

panel_bp = Blueprint("panel", __name__, url_prefix="/panel")

panel_bp.add_url_rule("profile", view_func=profile_index)
panel_bp.add_url_rule(
    "profile/new-password",
    view_func=profile_new_password,
    methods=["POST"]
)

panel_bp.add_url_rule("credentials", view_func=credentials_index)
panel_bp.add_url_rule(
    "credentials/shopee/<id>",
    view_func=credentials_shopee_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/shopee/<id>",
    view_func=credentials_shopee_del,
    methods=["DELETE"]
)
panel_bp.add_url_rule(
    "credentials/threads/<id>",
    view_func=credentials_threads_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/threads/<id>",
    view_func=credentials_threads_del,
    methods=["DELETE"]
)
