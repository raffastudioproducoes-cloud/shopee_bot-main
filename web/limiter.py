from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# instância sem app vinculado ainda — cada blueprint importa e decora
# suas rotas com isso; web/__init__.py chama limiter.init_app(app) e
# define os limites padrão depois que os blueprints já foram registrados
limiter = Limiter(
    key_func=get_remote_address,
    # teto padrão pra qualquer rota sem limite próprio — protege o
    # servidor de sobrecarga por excesso de requisição, não é
    # anti-brute-force (isso é o limite específico do login)
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"
)

