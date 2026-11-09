"""Cancelar campanha apaga os posts que nunca rodaram, sem desfazer o cancelamento se a limpeza falhar."""
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api import campaign_activation
from api.main import app
from api.routers import campaigns as campaigns_module
from api.routers.auth import get_current_user_id
from api.routers.profiles import get_current_profile_id

RID = uuid.uuid4()


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: 42
    app.dependency_overrides[get_current_profile_id] = lambda: "profile-a"
    rpcs = []
    monkeypatch.setattr(campaign_activation, "owned_reservation", lambda *a, **k: {"id": str(RID)})
    monkeypatch.setattr(campaign_activation, "reservation_details", lambda *a, **k: {"id": str(RID), "lifecycle": "cancelled"})
    monkeypatch.setattr(campaign_activation, "_rpc", lambda name, args: rpcs.append((name, args)))
    yield TestClient(app), rpcs
    app.dependency_overrides.clear()


def test_cancel_runs_the_purge_for_the_same_owner_and_reservation(client, monkeypatch):
    http, rpcs = client
    fake = MagicMock()
    monkeypatch.setattr(campaigns_module, "supabase", fake)
    res = http.post(f"/campaigns/active/{RID}/cancel")
    assert res.status_code == 200
    assert [name for name, _ in rpcs] == ["change_campaign_lifecycle_f4e"]
    fake.rpc.assert_called_once_with("purge_cancelled_campaign_f4e", {
        "p_user_id": "42", "p_profile_id": "profile-a", "p_reservation_id": str(RID)})


@pytest.mark.parametrize("action", ["pause", "resume"])
def test_pause_and_resume_never_purge(client, monkeypatch, action):
    http, _ = client
    fake = MagicMock()
    monkeypatch.setattr(campaigns_module, "supabase", fake)
    assert http.post(f"/campaigns/active/{RID}/{action}").status_code == 200
    fake.rpc.assert_not_called()


def test_a_failed_purge_does_not_undo_the_cancellation(client, monkeypatch):
    http, _ = client
    fake = MagicMock()
    fake.rpc.return_value.execute.side_effect = RuntimeError("boom")
    monkeypatch.setattr(campaigns_module, "supabase", fake)
    res = http.post(f"/campaigns/active/{RID}/cancel")
    assert res.status_code == 200 and res.json()["lifecycle"] == "cancelled"
