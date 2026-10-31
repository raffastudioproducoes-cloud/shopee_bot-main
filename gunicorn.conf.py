import logging
import os
import subprocess
import sys
import threading

from shopee_bot.web import post_fork, on_exit as _flask_on_exit

loglevel = "info"
# Plataformas (livemy.app, Hugging Face Spaces) injetam a porta em $PORT.
# Default 5000 mantém compatível com compose/local.
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
worker_class = "shopee_bot.scheduler.gunicorn_worker.PublishingGeventWorker"
# Finito: com timeout=0 um worker travado nunca seria reciclado. O worker
# gevent notifica o master em loop próprio, então 120s não mata requisição
# longa que esteja só aguardando I/O.
timeout = 120
# Give in-flight publications time to finish on rolling deploy.
# The queue will remain "unknown" if the host terminates us earlier.
graceful_timeout = 120

# FastAPI (api/main.py) sobe como processo uvicorn separado no mesmo
# container — gevent monkey-patch do Flask (web/__init__.py) é incompatível
# com montar ASGI no mesmo processo. Porta fixa 127.0.0.1:8001, só acessível
# de dentro do container (api/internal_client.py fala com o Flask, não o
# contrário; esse subprocesso é o lado FastAPI da mesma dupla).
_uvicorn_process = None

# CAUSA RAIZ do incidente de 2026-09-26 (confirmada lendo o source instalado
# de gunicorn==23.0.0 e uvicorn==0.34.0, não é hipótese):
#
# gunicorn.arbiter.Arbiter.reap_workers() reage a SIGCHLD chamando
# `os.waitpid(-1, os.WNOHANG)` — o pid=-1 reaps QUALQUER filho do processo
# master, não só os workers gevent que o próprio gunicorn deu fork. Esse
# subprocesso uvicorn, criado via subprocess.Popen aqui embaixo, é filho
# direto do master e cai nesse mesmo laço.
#
# Pior: antes mesmo de checar se o pid pertence a um worker conhecido
# (`if wpid not in self.WORKERS`), o reap_workers já testa
# `exitcode == self.WORKER_BOOT_ERROR` (=3) / `APP_LOAD_ERROR` (=4) e, se
# bater, dá `raise HaltServer(...)` — derrubando o master inteiro (Flask
# junto). uvicorn, de forma totalmente independente, usa exit code 3
# (`STARTUP_FAILURE`, uvicorn/main.py) quando o lifespan `startup` da app
# ASGI falha (ex.: o RuntimeError de Supabase ausente em api/database.py).
# Os dois valores (3) colidirem é coincidência, mas o efeito é: qualquer
# falha de startup do FastAPI matava o Flask junto.
#
# Correção: nunca deixar esse subprocesso terminar com exit code 3 ou 4.
# Em vez de invocar o binário `uvicorn` (que chama sys.exit(STARTUP_FAILURE)
# direto), rodamos `uvicorn.run(...)` dentro de um subprocesso Python que
# intercepta o SystemExit e reemite qualquer 3/4 como um código inofensivo.
# Continua sendo um único processo (mesmo pid), então o terminate()/wait()
# em on_exit() abaixo não muda.
_UVICORN_ENTRYPOINT = (
    "import sys\n"
    "import uvicorn\n"
    "try:\n"
    "    uvicorn.run('api.main:app', host='127.0.0.1', port=8001)\n"
    "except SystemExit as exc:\n"
    "    code = exc.code if isinstance(exc.code, int) else 1\n"
    "    sys.exit(70 if code in (3, 4) else code)\n"
)


_log = logging.getLogger("gunicorn.error")
_SUPERVISOR_POLL_SECONDS = 5
_SUPERVISOR_MAX_BACKOFF_SECONDS = 60
_supervisor_stop = threading.Event()


def _start_uvicorn():
    return subprocess.Popen([sys.executable, "-c", _UVICORN_ENTRYPOINT])


def _supervise_uvicorn():
    """Reinicia o uvicorn se o subprocesso morrer, com backoff exponencial
    (1s, 2s, 4s... até 60s; volta a 1s depois que fica de pé)."""
    global _uvicorn_process
    backoff = 1
    while not _supervisor_stop.wait(_SUPERVISOR_POLL_SECONDS):
        code = _uvicorn_process.poll()
        if code is None:
            backoff = 1
            continue
        _log.error("uvicorn saiu com código %s; reiniciando em %ss", code, backoff)
        if _supervisor_stop.wait(backoff):
            break
        if _supervisor_stop.is_set():  # on_exit já rodou: não criar uvicorn órfão
            break
        _uvicorn_process = _start_uvicorn()
        backoff = min(backoff * 2, _SUPERVISOR_MAX_BACKOFF_SECONDS)


# Server Hooks
post_fork = post_fork


def worker_exit(server, worker):
    """Scheduler runs inside the gevent worker, not the Gunicorn master."""
    try:
        from shopee_bot.scheduler import shutdown_gracefully
        shutdown_gracefully()
    except Exception:
        _log.exception("Falha ao encerrar scheduler do worker")


def on_starting(server):
    global _uvicorn_process
    _uvicorn_process = _start_uvicorn()
    threading.Thread(target=_supervise_uvicorn, name="uvicorn-supervisor", daemon=True).start()


def on_exit(server):
    _supervisor_stop.set()
    _flask_on_exit(server)
    if _uvicorn_process is not None:
        _uvicorn_process.terminate()
        try:
            _uvicorn_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _uvicorn_process.kill()
            _uvicorn_process.wait(timeout=5)
