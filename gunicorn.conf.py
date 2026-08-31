import os

from shopee_bot.web import post_fork, on_exit

loglevel = "info"
# Plataformas (livemy.app, Hugging Face Spaces) injetam a porta em $PORT.
# Default 5000 mantém compatível com compose/local.
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 1
worker_class = "gevent"
timeout = 0


# Server Hooks
post_fork = post_fork
on_exit = on_exit
