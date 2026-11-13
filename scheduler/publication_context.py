"""Fronteira durável entre preparação local e envio externo.

Apenas o worker que detém o claim pode avançar para a rede social. Esta
barreira não resolve o caso em que a API aceitou o POST mas a resposta sumiu:
esse resultado permanece 'unknown' até conciliação humana/oficial.
"""

from contextvars import ContextVar

from shopee_bot.database import publish_jobs
from shopee_bot.database import post_content_snapshot


_active_attempt = ContextVar("active_publish_attempt", default=None)


class PublicationDeferred(BaseException):
    """Controle interno: interromper ANTES da rede, sem engolir em except Exception."""


def activate(publish_job_id, claim_token, content_snapshot=None):
    attempt_token = _active_attempt.set((publish_job_id, claim_token))
    snapshot_token = post_content_snapshot.bind(content_snapshot)
    return attempt_token, snapshot_token


def reset(tokens):
    attempt_token, snapshot_token = tokens
    post_content_snapshot.reset(snapshot_token)
    _active_attempt.reset(attempt_token)


def active_publish_job_id():
    """ID do envio em execução neste contexto (ou None fora de uma publicação)."""
    attempt = _active_attempt.get()
    return attempt[0] if attempt else None


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
    from shopee_bot.scheduler import campaign_dispatch
    if campaign_dispatch.campaign_execution_enabled():
        permitted = campaign_dispatch.mark_external_started(*attempt)
    else:
        permitted = publish_jobs.mark_external_started(*attempt)
    if not permitted:
        raise PublicationDeferred("Claim ou autorização perdido antes do envio externo")
