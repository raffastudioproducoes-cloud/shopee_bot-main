from flask import Blueprint

from shopee_bot.web.routes.panel.profile import profile_index, \
    profile_new_password
from shopee_bot.web.routes.panel.credentials import credentials_index, \
    credentials_shopee_save, credentials_shopee_del, \
    credentials_threads_save, credentials_threads_del, \
    credentials_x_save, credentials_x_del, \
    credentials_facebook_save, credentials_facebook_del, \
    credentials_instagram_save, credentials_instagram_del, \
    credentials_tiktok_save, credentials_tiktok_del, \
    credentials_kwai_save, credentials_kwai_del

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
    methods=["GET", "POST"]
)
panel_bp.add_url_rule(
    "credentials/threads/<id>",
    view_func=credentials_threads_del,
    methods=["DELETE"]
)
panel_bp.add_url_rule(
    "credentials/x/<id>",
    view_func=credentials_x_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/x/<id>",
    view_func=credentials_x_del,
    methods=["DELETE"]
)
panel_bp.add_url_rule(
    "credentials/facebook/<id>",
    view_func=credentials_facebook_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/facebook/<id>",
    view_func=credentials_facebook_del,
    methods=["DELETE"]
)
panel_bp.add_url_rule(
    "credentials/instagram/<id>",
    view_func=credentials_instagram_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/instagram/<id>",
    view_func=credentials_instagram_del,
    methods=["DELETE"]
)
panel_bp.add_url_rule(
    "credentials/tiktok/<id>",
    view_func=credentials_tiktok_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/tiktok/<id>",
    view_func=credentials_tiktok_del,
    methods=["DELETE"]
)
panel_bp.add_url_rule(
    "credentials/kwai/<id>",
    view_func=credentials_kwai_save,
    methods=["POST"]
)
panel_bp.add_url_rule(
    "credentials/kwai/<id>",
    view_func=credentials_kwai_del,
    methods=["DELETE"]
)
