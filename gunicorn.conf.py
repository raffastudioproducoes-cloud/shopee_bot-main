import os

from shopee_bot.web import on_starting, on_exit

loglevel = "info"
# Plataformas (livemy.app, Hugging Face Spaces) injetam a porta em $PORT.
# Default 5000 mantém compatível com compose/local.
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
worker_class = "gevent"
timeout = 0


# Server Hooks
on_starting = on_starting
on_exit = on_exit
