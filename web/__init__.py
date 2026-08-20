# fmt: on
from gevent import monkey
monkey.patch_all()
# fmt: off

import os
from shopee_bot.web.user import User
from shopee_bot.database import init as init_db, close_connection, users
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

# proxy fix
# https://github.com/pallets-eco/flask-wtf/issues/455
app.config['WTF_CSRF_SSL_STRICT'] = False
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# CSRF
csrf = CSRFProtect(app)

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
    return render_template("index.html", user=current_user)


# development only, production uses Nginx
@app.get("/media/<path:name>")
def data_view(name):
    return send_from_directory('media', name)


# Gunicon Server Hooks
def on_starting(server):
    init_db()
    init_scheduler()


def on_exit(server):
    close_connection()


if DEBUG:
    init_db()
    init_scheduler()
