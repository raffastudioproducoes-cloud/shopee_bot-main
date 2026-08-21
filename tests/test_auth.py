"""Fluxo crítico: login."""


def test_login_success(client, test_user):
    res = client.post(
        "/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"],
            "next": "",
        },
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["Location"] == "/"


def test_login_wrong_password(client, test_user):
    res = client.post(
        "/auth/login",
        data={
            "username": test_user["username"],
            "password": "senha_errada",
            "next": "",
        },
    )
    assert res.status_code == 400


def test_login_unknown_user(client):
    res = client.post(
        "/auth/login",
        data={"username": "nao_existe_de_verdade", "password": "x", "next": ""},
    )
    assert res.status_code == 400
