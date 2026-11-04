"""Contrato F4E-2B2 de identidade de campanha, ainda sem autoridade de despacho.

Os identificadores espelham os tipos reais de banco: scheduler e publish_job
sao UUID, enquanto posts.id e INTEGER. Um objeto em memoria NUNCA prova
vinculo no Supabase, titularidade, imutabilidade ou aprovacao para publicar.
A guarda permanece incondicionalmente fechada ate haver verificacao atomica
no claim/retry e imediatamente antes de qualquer operacao no provedor, com
a mesma protecao implantada em ambos os ambientes.
"""
from dataclasses import dataclass
from uuid import UUID


class CampaignDispatchBlocked(RuntimeError):
    """Envio de campanha indisponivel nesta etapa."""


# X permanece indisponivel no produto; Kwai e Shopee Video nao publicam.
_CAMPAIGN_NETWORKS = frozenset({"threads", "facebook", "instagram", "tiktok"})


@dataclass(frozen=True)
class CampaignDispatchIdentity:
    """Somente formato de identidade; sem consulta ou permissao de publicacao."""

    user_id: UUID
    profile_id: UUID
    reservation_id: UUID
    occurrence_id: UUID
    scheduler_id: UUID
    publish_job_id: UUID
    post_id: int
    network: str
    source_environment: str

    def __post_init__(self):
        for value in (
            self.user_id, self.profile_id, self.reservation_id,
            self.occurrence_id, self.scheduler_id, self.publish_job_id,
        ):
            if not isinstance(value, UUID) or value.int == 0:
                raise ValueError("Identidade UUID de campanha invalida")
        if type(self.post_id) is not int or self.post_id < 1:
            raise ValueError("Identidade numerica de post invalida")
        if self.network not in _CAMPAIGN_NETWORKS:
            raise ValueError("Rede de campanha indisponivel")
        if self.source_environment not in ("production", "staging"):
            raise ValueError("Ambiente de origem invalido")


def require_campaign_dispatch_authorization(identity: object) -> None:
    """Gate incondicional: nem formato valido nem flags permitem publicacao.

    A futura autorizacao exigira identidade persistente verificada em transacao
    e revogavel por downgrade/cancelamento. Esta funcao nao consulta o banco
    e NAO deve ser substituida por verificacao apenas em memoria.
    """
    raise CampaignDispatchBlocked("Dispatch de campanha indisponivel")
