# fmt: on
from gevent import monkey
monkey.patch_all()
# fmt: off

from pathlib import Path
import os
from shopee_bot.web.user import User
from shopee_bot.database import init as init_db, close_connection, users, \
    products, posts, product_lists, activities
from shopee_bot.scheduler import init as init_scheduler, scheduler_enabled
from shopee_bot.web.routes.panel import panel_bp
from shopee_bot.web.routes.product_lists import product_lists_bp
from shopee_bot.web.routes.products import products_bp
from shopee_bot.web.routes.users import users_bp
from shopee_bot.web.routes.activities import activities_bp
from shopee_bot.web.routes.auth import auth_bp
from shopee_bot.web.routes.startup import startup_bp
from shopee_bot.web.routes.internal import internal_bp
from shopee_bot.web.routes.api_proxy import api_proxy_bp
from shopee_bot.web.routes.spa import spa_bp
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_required, current_user
from flask_cors import CORS
from shopee_bot.web.limiter import limiter
from shopee_bot.web.helpers import cors_origins
from flask import Flask, render_template, request, send_from_directory
from dotenv import load_dotenv
load_dotenv()

SESSION_SECRET = os.environ.get("FLASK_SESSION_SECRET")
UPLOAD_FOLDER = os.environ.get("FLASK_UPLOAD_FOLDER")
MAX_CONTENT_LENGTH = int(os.environ.get("FLASK_MAX_CONTENT_LENGTH"))
DEBUG = os.environ.get("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}

# Painel Jinja legado (index() em "/", + blueprints products/users)
# colide de path com o React novo (frontend/, ver router.tsx). Default
# "false": React é o painel principal daqui pra frente, essas 4 rotas
# ficam fora e o catch-all do SPA (web/routes/spa.py) assume os paths.
# "true" reverte pro Jinja antigo (rollback reversível, sem rebuild).
LEGACY_PANEL_ENABLED = os.environ.get(
    "LEGACY_PANEL_ENABLED", "false"
).lower() == "true"

# app — static_folder absoluto baseado na localização do módulo para
# funcionar tanto em dev local quanto em Docker/livemy (onde o root
# do app é /shopee_bot/web e os assets estão em ../static = web/static)
_app_dir = Path(__file__).resolve().parent
app = Flask(
    __name__,
    static_folder=_app_dir / 'static',
    static_url_path='/static'
)
# CORS só pras origens configuradas (antes: CORS(app) = qualquer origem,
# inclusive no proxy /api). Sem nenhuma configurada, não liga CORS: o SPA
# é servido pelo próprio Flask (mesma origem).
_cors_origins = cors_origins()
if _cors_origins:
    CORS(app, origins=_cors_origins)

# session cookie security
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_SESSION_COOKIE_SECURE", "False").lower() == "true"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.secret_key = SESSION_SECRET

# proxy fix
# https://github.com/pallets-eco/flask-wtf/issues/455
app.config['WTF_CSRF_SSL_STRICT'] = False
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# CSRF
csrf = CSRFProtect(app)

# security headers — aplicados em todas as respostas
_LEGACY_TEMPLATE_ENDPOINT_PREFIXES = (
    "activities.", "auth.", "panel.", "product_lists.", "products.", "users.",
)


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    endpoint = request.endpoint or ""
    legacy_template = LEGACY_PANEL_ENABLED and (
        endpoint == "index" or endpoint.startswith(_LEGACY_TEMPLATE_ENDPOINT_PREFIXES)
    )
    script_src = (
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
        if legacy_template else "script-src 'self'"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"{script_src}; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' https://*.supabase.co https://graph.threads.net; "
        "frame-ancestors 'none'"
    )
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    return response

# tratamento genérico de exceções — evita information disclosure
@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    cls_name = type(e).__name__
    # erro do CSRFProtect não deve vazar detalhes internos
    if cls_name == "CSRFError":
        return {"error": "Requisição inválida"}, 400
    # no DEBUG, Flask ainda retorna o traceback padrão; em produção,
    # o werkzeug error handler assume; aqui garantimos resposta JSON
    # genérica para rotas que não foram tratadas pelo CSRF ou por
    # handlers específicos
    if not DEBUG:
        return {"error": "Ocorreu um erro interno. Tente novamente."}, 500
    return {"error": f"{cls_name}: {e}"}, 500

# rate limiting — limite padrão global (ver web/limiter.py) mais o
# limite específico do login (ver web/routes/auth.py)
limiter.init_app(app)

# Babel for flask_wtf
app.config['BABEL_DEFAULT_LOCALE'] = 'pt_BR'
babel = Babel(app)

# initialize routes
app.register_blueprint(startup_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(activities_bp)
if LEGACY_PANEL_ENABLED:
    app.register_blueprint(users_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(panel_bp)
app.register_blueprint(product_lists_bp)
# rotas internas (chamadas só pela API nova, via secret — não sessão de
# browser) precisam ficar fora do CSRF, que exige token de sessão
app.register_blueprint(internal_bp)
csrf.exempt(internal_bp)
# proxy /api/* pro FastAPI interno (127.0.0.1:8001) — tem seu próprio
# JWT/cookie, não usa sessão Flask-WTF, então fica fora do CSRF também
app.register_blueprint(api_proxy_bp)
csrf.exempt(api_proxy_bp)


# initialize flask-login
app.secret_key = SESSION_SECRET.encode("ascii")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login_get"
login_manager.login_message = "Faça o login para obter o acesso."
login_manager.refresh_view = "auth.login_get"
login_manager.needs_refresh_message = "Para proteger a sua conta, refaça o login."


# file upload
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Health check endpoint for monitoring (UptimeRobot, etc.)
# Public, no auth required, returns 200 OK when app is running.
@app.get("/health")
def health():
    return {"status": "ok"}, 200


# Verifica se a pasta de uploads existe, senão cria
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Carregador de usuário
@login_manager.user_loader
def load_user(user_id):
    user = users.get(user_id)
    if user and user["id"] == user_id:
        username = user["username"]
        access = user["access"]
        return User(user_id, username, access)
    return None


if LEGACY_PANEL_ENABLED:
    @app.get("/")
    @login_required
    def index():
        recent_posts, _ = posts.query_paginated(current_user.id, None, 5)
        recent_activities, _ = activities.query_activities_paginated(
            current_user.id, None, 5
        )

        return render_template(
            "index.html",
            user=current_user,
            products_count=products.count(current_user.id),
            posts_count=posts.count(current_user.id),
            product_lists_count=product_lists.count(current_user.id),
            recent_posts=recent_posts,
            recent_activities=recent_activities,
        )


# development only, production uses Nginx
@app.get("/media/<path:name>")
def data_view(name):
    return send_from_directory('media', name)


# catch-all do SPA React (frontend/dist) — precisa ser o ÚLTIMO registro
# do arquivo: Werkzeug desempata rotas de mesmo "peso" (ex.: "/" estático
# vs "/" via defaults do catch-all) pela ordem de inserção, então
# registrar antes faria o catch-all vencer index()/data_view() mesmo com
# LEGACY_PANEL_ENABLED=true. Registrado por último, rotas Flask exatas já
# definidas acima sempre vencem o <path:...> do catch-all; só os paths que
# ninguém registrou (ou que ficaram fora por causa da flag) chegam aqui.
app.register_blueprint(spa_bp)


# Gunicon Server Hooks
def post_fork(server, worker):
    init_db()
    if scheduler_enabled():
        init_scheduler()


def on_exit(server):
    close_connection()


if DEBUG:
    init_db()
    if scheduler_enabled():
        init_scheduler()
