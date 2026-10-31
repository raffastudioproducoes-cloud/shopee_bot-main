"""Fronteira durável entre preparação local e envio externo.

Apenas o worker que detém o claim pode avançar para a rede social. Esta
barreira não resolve o caso em que a API aceitou o POST mas a resposta sumiu:
esse resultado permanece 'unknown' até conciliação humana/oficial.
"""

from contextvars import ContextVar

from shopee_bot.database import publish_jobs


_active_attempt = ContextVar("active_publish_attempt", default=None)


class PublicationDeferred(BaseException):
    """Controle interno: interromper ANTES da rede, sem engolir em except Exception."""


def activate(publish_job_id, claim_token):
    return _active_attempt.set((publish_job_id, claim_token))


def reset(token):
    _active_attempt.reset(token)


def mark_external_delivery():
    """Chamar logo antes do primeiro POST/upload de publicação no provedor.

    Chamadas diretas em testes/utilitários sem uma fila ativa continuam válidas.
    Nenhuma publicação real começa se a instância está encerrando ou perdeu
    o claim. Uma falha de gravação também bloqueia o envio por segurança.
    """
    attempt = _active_attempt.get()
    if attempt is None:
        return
    from shopee_bot.scheduler import is_shutting_down

    if is_shutting_down():
        raise PublicationDeferred("Worker encerrando antes do envio externo")
    if not publish_jobs.mark_external_started(*attempt):
        raise PublicationDeferred("Claim perdido antes do envio externo")
