import os
import subprocess

from shopee_bot.web import post_fork, on_exit as _flask_on_exit

loglevel = "info"
# Plataformas (livemy.app, Hugging Face Spaces) injetam a porta em $PORT.
# Default 5000 mantém compatível com compose/local.
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
worker_class = "gevent"
timeout = 0

# FastAPI (api/main.py) sobe como processo uvicorn separado no mesmo
# container — gevent monkey-patch do Flask (web/__init__.py) é incompatível
# com montar ASGI no mesmo processo. Porta fixa 127.0.0.1:8001, só acessível
# de dentro do container (api/internal_client.py fala com o Flask, não o
# contrário; esse subprocesso é o lado FastAPI da mesma dupla).
_uvicorn_process = None


# Server Hooks
post_fork = post_fork


def on_starting(server):
    global _uvicorn_process
    _uvicorn_process = subprocess.Popen(
        ["uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8001"]
    )


def on_exit(server):
    _flask_on_exit(server)
    if _uvicorn_process is not None:
        _uvicorn_process.terminate()
        try:
            _uvicorn_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _uvicorn_process.kill()
            _uvicorn_process.wait(timeout=5)
