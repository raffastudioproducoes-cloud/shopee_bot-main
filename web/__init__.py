# fmt: on
from gevent import monkey
monkey.patch_all()
# fmt: off

import os
from shopee_bot.web.user import User
from shopee_bot.database import init as init_db, close_connection, users, \
    products, posts, product_lists, activities
from shopee_bot.scheduler import init as init_scheduler
from shopee_bot.web.routes.posts import posts_bp
from shopee_bot.web.routes.panel import panel_bp
from shopee_bot.web.routes.product_lists import product_lists_bp
from shopee_bot.web.routes.products import products_bp
from shopee_bot.web.routes.users import users_bp
from shopee_bot.web.routes.activities import activities_bp
from shopee_bot.web.routes.auth import auth_bp
from shopee_bot.web.routes.startup import startup_bp
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_required, current_user
from flask_cors import CORS
from shopee_bot.web.limiter import limiter
from flask import Flask, render_template, send_from_directory
from dotenv import load_dotenv
load_dotenv()

SESSION_SECRET = os.environ.get("FLASK_SESSION_SECRET")
UPLOAD_FOLDER = os.environ.get("FLASK_UPLOAD_FOLDER")
MAX_CONTENT_LENGTH = int(os.environ.get("FLASK_MAX_CONTENT_LENGTH"))
DEBUG = bool(os.environ.get("FLASK_DEBUG"))

# app
app = Flask(__name__)
CORS(app)

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
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
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
app.register_blueprint(users_bp)
app.register_blueprint(products_bp)
app.register_blueprint(product_lists_bp)
app.register_blueprint(panel_bp)
app.register_blueprint(posts_bp)


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


# Gunicon Server Hooks
def post_fork(server, worker):
    init_db()
    init_scheduler()


def on_exit(server):
    close_connection()


if DEBUG:
    init_db()
    init_scheduler()
