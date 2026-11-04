"""F4E-2B2: formato fiel ao schema e bloqueio incondicional do envio."""
from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from shopee_bot.database.campaign_dispatch_guard import (
    CampaignDispatchBlocked,
    CampaignDispatchIdentity,
    require_campaign_dispatch_authorization,
)

U = UUID("11111111-1111-4111-8111-111111111111")
P = UUID("22222222-2222-4222-8222-222222222222")
R = UUID("33333333-3333-4333-8333-333333333333")
O = UUID("44444444-4444-4444-8444-444444444444")
S = UUID("55555555-5555-4555-8555-555555555555")
J = UUID("66666666-6666-4666-8666-666666666666")


def identity(**changes):
    values = dict(
        user_id=U, profile_id=P, reservation_id=R, occurrence_id=O,
        scheduler_id=S, publish_job_id=J, post_id=2,
        network="threads", source_environment="staging",
    )
    values.update(changes)
    return CampaignDispatchIdentity(**values)


@pytest.mark.parametrize("environment", ["staging", "production"])
@pytest.mark.parametrize("flag", ["false", "true"])
def test_even_well_formed_identity_never_authorizes_dispatch(environment, flag, monkeypatch):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", flag)
    with pytest.raises(CampaignDispatchBlocked):
        require_campaign_dispatch_authorization(identity(source_environment=environment))


@pytest.mark.parametrize("candidate", [None, {}, "legacy", False])
def test_missing_or_untrusted_identity_never_authorizes_dispatch(candidate):
    with pytest.raises(CampaignDispatchBlocked):
        require_campaign_dispatch_authorization(candidate)


@pytest.mark.parametrize("changes", [
    {"user_id": None}, {"profile_id": str(P)},
    {"reservation_id": UUID(int=0)}, {"occurrence_id": None},
    {"scheduler_id": 7}, {"publish_job_id": 8},
    {"scheduler_id": UUID(int=0)}, {"publish_job_id": None},
    {"post_id": 0}, {"post_id": True}, {"post_id": -1},
    {"network": "x"}, {"network": "kwai"}, {"network": "THREADS"},
    {"network": None}, {"source_environment": "preview"},
    {"source_environment": None},
])
def test_malformed_identity_is_rejected(changes):
    with pytest.raises(ValueError):
        identity(**changes)


def test_identity_has_real_database_column_types_and_is_memory_only():
    candidate = identity()
    assert isinstance(candidate.scheduler_id, UUID)
    assert isinstance(candidate.publish_job_id, UUID)
    assert type(candidate.post_id) is int
    with pytest.raises(FrozenInstanceError):
        candidate.publish_job_id = J
    with pytest.raises(CampaignDispatchBlocked):
        require_campaign_dispatch_authorization(candidate)
