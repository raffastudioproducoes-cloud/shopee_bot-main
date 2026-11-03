"""Contrato experimental F4E-2B1, isolado dos executores existentes.

Identidade neste objeto e somente uma representacao em memoria: nao comprova
origem, ownership, vinculo persistido, imutabilidade no banco ou autorizacao.
A funcao de bloqueio SEMPRE recusa, inclusive com flag central ligada.
Nao integrar como autorizacao de despacho nem criar campanhas com ela.
"""
from dataclasses import dataclass
from uuid import UUID


class CampaignDispatchBlocked(RuntimeError):
    """Envio de campanha indisponivel nesta etapa."""


@dataclass(frozen=True)
class CampaignDispatchIdentity:
    """Formato candidato; nao e identidade confiavel nem persistida."""

    user_id: UUID
    profile_id: UUID
    reservation_id: UUID
    occurrence_id: UUID
    job_id: int
    post_id: int
    source_environment: str

    def __post_init__(self):
        for value in (self.user_id, self.profile_id, self.reservation_id, self.occurrence_id):
            if not isinstance(value, UUID) or value.int == 0:
                raise ValueError("Identidade UUID de campanha invalida")
        for value in (self.job_id, self.post_id):
            if type(value) is not int or value < 1:
                raise ValueError("Identidade numerica de campanha invalida")
        if self.source_environment not in ("production", "staging"):
            raise ValueError("Ambiente de origem invalido")


def require_campaign_dispatch_authorization(identity: object) -> None:
    """Gate provisório incondicional: nenhuma entrada habilita envio.

    Nunca substituir a futura checagem atomica no claim e imediatamente antes
    da primeira operacao externa. Nao consulta ambiente, banco ou provedor.
    """
    raise CampaignDispatchBlocked("Dispatch de campanha indisponivel")
