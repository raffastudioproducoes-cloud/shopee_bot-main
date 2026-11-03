"""Contrato F4E-2B1: nenhum caminho autoriza envio ou acessa rede/banco."""
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


def identity(**changes):
    values = dict(user_id=U, profile_id=P, reservation_id=R, occurrence_id=O,
                  job_id=1, post_id=2, source_environment="staging")
    values.update(changes)
    return CampaignDispatchIdentity(**values)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_even_well_formed_identity_never_authorizes_dispatch(environment, monkeypatch):
    monkeypatch.setenv("ORBITAL_CENTRAL_DISPATCH_ENABLED", "true")
    with pytest.raises(CampaignDispatchBlocked):
        require_campaign_dispatch_authorization(identity(source_environment=environment))


@pytest.mark.parametrize("candidate", [None, {}, "legacy", False])
def test_missing_or_untrusted_identity_never_authorizes_dispatch(candidate):
    with pytest.raises(CampaignDispatchBlocked):
        require_campaign_dispatch_authorization(candidate)


@pytest.mark.parametrize("changes", [
    {"user_id": None}, {"profile_id": "22222222-2222-4222-8222-222222222222"},
    {"reservation_id": UUID(int=0)}, {"occurrence_id": None},
    {"job_id": 0}, {"job_id": True}, {"post_id": -1},
    {"source_environment": "preview"}, {"source_environment": None},
])
def test_malformed_identity_is_rejected(changes):
    with pytest.raises(ValueError):
        identity(**changes)


def test_identity_is_immutable_only_in_memory():
    candidate = identity()
    with pytest.raises(FrozenInstanceError):
        candidate.job_id = 3
