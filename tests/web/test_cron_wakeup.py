
from unittest.mock import MagicMock
from types import SimpleNamespace

import shopee_bot.scheduler as scheduler


ROUTE = "/_ops/scheduler/wake"


def test_wakeup_sem_token(client, monkeypatch):
    monkeypatch.setenv("ORBITAL_WAKE_SECRET", "segredo-de-teste")

    response = client.post(ROUTE)

    assert response.status_code == 404


def test_wakeup_com_token_incorreto(client, monkeypatch):
    monkeypatch.setenv("ORBITAL_WAKE_SECRET", "segredo-de-teste")

    response = client.post(
        ROUTE,
        headers={"Authorization": "Bearer outro-segredo"},
    )

    assert response.status_code == 404


def test_wakeup_sem_configuracao(client, monkeypatch):
    monkeypatch.delenv("ORBITAL_WAKE_SECRET", raising=False)

    response = client.post(
        ROUTE,
        headers={"Authorization": "Bearer qualquer-valor"},
    )

    assert response.status_code == 404


def test_wakeup_autorizado(client, monkeypatch):
    monkeypatch.setenv("ORBITAL_WAKE_SECRET", "segredo-de-teste")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")

    wakeup = MagicMock()

    fake_scheduler = SimpleNamespace(
        running=True,
        wakeup=wakeup,
    )

    monkeypatch.setattr(
        scheduler,
        "_scheduler",
        fake_scheduler,
    )

    response = client.post(
        ROUTE,
        headers={
            "Authorization": "Bearer segredo-de-teste"
        },
    )

    assert response.status_code == 204
    wakeup.assert_called_once_with()


def test_wakeup_sem_scheduler_ativo(client, monkeypatch):
    monkeypatch.setenv("ORBITAL_WAKE_SECRET", "segredo-de-teste")
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    response = client.post(
        ROUTE,
        headers={
            "Authorization": "Bearer segredo-de-teste"
        },
    )

    assert response.status_code == 503
