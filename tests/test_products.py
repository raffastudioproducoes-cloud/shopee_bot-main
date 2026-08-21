"""Fluxo crítico: criar produto."""
from shopee_bot.database import products


def _login(client, test_user):
    client.post(
        "/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"],
            "next": "",
        },
    )


def test_create_product(client, test_user):
    _login(client, test_user)

    before = products.count(test_user["id"])

    res = client.post(
        "/products",
        data={
            "product_id": "999888777",
            "name": "Produto de teste automatizado",
            "original_link": "https://shopee.com.br/teste-999888777",
            "commission_link": "https://s.shopee.com.br/teste",
            "commission": "R$ 5,00",
            "image": "https://picsum.photos/200",
            "price_min": "R$ 10,00",
            "price_max": "R$ 20,00",
        },
    )

    assert res.status_code == 201
    assert products.count(test_user["id"]) == before + 1


def test_create_product_requires_login(client):
    res = client.post("/products", data={"name": "sem login"})
    assert res.status_code in (302, 401)
