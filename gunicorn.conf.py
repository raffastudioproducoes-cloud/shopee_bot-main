from shopee_bot.web import on_starting, on_exit

loglevel = "info"
bind = "0.0.0.0:5000"
workers = 1
worker_class = "gevent"
timeout = 0


# Server Hooks
on_starting = on_starting
on_exit = on_exit
