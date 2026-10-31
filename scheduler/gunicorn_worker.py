"""Worker Gunicorn que drena o APScheduler DURANTE o shutdown.

worker_exit roda depois que o worker saiu: é tarde demais para esperar por
Threads/Facebook/Instagram/TikTok. O finally de run() roda ainda no processo
vivo, após o Gunicorn receber SIGTERM e sair do loop de atendimento.
"""

from gunicorn.workers.ggevent import GeventWorker


class PublishingGeventWorker(GeventWorker):
    def handle_exit(self, sig, frame):
        # Handler leve: não bloqueia o loop de sinais do Gunicorn.
        from shopee_bot.scheduler import mark_shutting_down

        mark_shutting_down()
        super().handle_exit(sig, frame)

    def run(self):
        try:
            return super().run()
        finally:
            from shopee_bot.scheduler import shutdown_gracefully

            shutdown_gracefully()
