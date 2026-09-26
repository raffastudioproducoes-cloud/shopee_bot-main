"""
Conftest isolado pra tests/scheduler/ — testa código do lado Flask
(pacote `shopee_bot.*`) sem precisar de Postgres local nem do
monkey-patch do gevent do conftest.py raiz (que trava o TestClient e
exige um Postgres real só pra rodar `shopee_bot.database.init()`).

Mesma ideia de tests/api/conftest.py: rode com
`pytest --confcutdir=tests/scheduler tests/scheduler` pra excluir o
conftest raiz da coleta. Os testes aqui mockam toda função que tocaria
o banco (schedulers.get_by_id, *_credentials.get_by_user_id, posts.get,
etc.) — não abrem conexão de verdade.
"""

import os
import sys
import types

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

try:
    import shopee_bot  # noqa: F401
except ModuleNotFoundError:
    pkg = types.ModuleType("shopee_bot")
    pkg.__path__ = [PROJECT_ROOT]
    sys.modules["shopee_bot"] = pkg

os.environ.setdefault("LOG_LEVEL", "30")
os.environ.setdefault(
    "APP_ENCRYPTION_KEY", "e7lc8f3AsY0VNg7Kpy1K5umJirUK6jwqkJg7_xhn0IY="
)
