"""Testa a whitelist de `func` em web/routes/internal.py::create_job.

Sem isso, `func` vinha direto do corpo da requisição (só protegido pelo
segredo compartilhado) até `globals()[func]` em scheduler/__init__.py —
um nome fora do NETWORK_FUNC_MAP resolveria qualquer símbolo importado
naquele módulo. Mocka add_job pra não precisar de Postgres/scheduler de
verdade.
"""

from unittest.mock import patch

INTERNAL_SECRET = "test-internal-secret"


def _headers():
    return {"X-Internal-Secret": INTERNAL_SECRET}


def test_create_job_rejects_func_outside_whitelist(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_SECRET", INTERNAL_SECRET)

    with patch("shopee_bot.web.routes.internal.add_job") as mock_add_job:
        res = client.post(
            "/internal/scheduler/jobs",
            json={
                "user_id": 1,
                "post_id": 1,
                "func": "os.system",
                "trigger": "date",
                "run_date": "2026-01-01T00:00:00",
            },
            headers=_headers(),
        )

    assert res.status_code == 400
    mock_add_job.assert_not_called()


def test_create_job_accepts_whitelisted_func(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_SECRET", INTERNAL_SECRET)

    with patch("shopee_bot.web.routes.internal.add_job", return_value=123) as mock_add_job:
        res = client.post(
            "/internal/scheduler/jobs",
            json={
                "user_id": 1,
                "post_id": 1,
                "func": "bot_post_x",
                "trigger": "date",
                "run_date": "2026-01-01T00:00:00",
            },
            headers=_headers(),
        )

    assert res.status_code == 201
    mock_add_job.assert_called_once()
