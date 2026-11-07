"""CPF protegido, leitura por conta e pré-condições futuras do gateway."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.account_identity import cpf_record, normalize_cpf, normalize_phone, purchase_readiness
from api.main import app
from api.routers import users as users_router
from api.routers.auth import get_current_user_id


def test_validates_cpf_and_stores_only_ciphertext_and_hmac():
    assert normalize_cpf("529.982.247-25") == "52998224725"
    with pytest.raises(HTTPException):
        normalize_cpf("111.111.111-11")
    with pytest.raises(HTTPException):
        normalize_cpf("529.982.247-26")
    record = cpf_record("529.982.247-25")
    assert "52998224725" not in str(record)
    assert len(record["cpf_fingerprint"]) == 64
    assert cpf_record("52998224725")["cpf_fingerprint"] == record["cpf_fingerprint"]
    assert cpf_record("52998224725")["cpf_ciphertext"] != record["cpf_ciphertext"]


def test_purchase_requirements_only_four_mandatory():
    user = {"email": "user@example.com"}
    row = {"full_name": "Cliente Teste", "cpf_ciphertext": "encrypted", "mobile_phone": None}
    assert purchase_readiness(user, row) == {"ready": False, "missing": ["Celular"]}
    row["mobile_phone"] = "21999998888"
    assert purchase_readiness(user, row) == {"ready": True, "missing": []}
    assert purchase_readiness({"email": None}, None)["missing"] == [
        "Nome e sobrenome", "CPF", "E-mail", "Celular",
    ]


def test_phone_accepts_international_ddi_without_breaking_legacy_brazilian_numbers():
    assert normalize_phone("(21) 99999-8888", mobile=True) == "21999998888"
    assert normalize_phone("+55 (21) 99999-8888", mobile=True) == "+5521999998888"
    assert normalize_phone("+1 (415) 555-1234", mobile=True) == "+14155551234"
    assert normalize_phone("+351 912 345 678") == "+351912345678"
    assert normalize_phone("") is None
    for invalid in ("+55 (21) 8888-8888", "+0 123456789", "+1 22", "+12 345 abc", "+1234567890123456"):
        with pytest.raises(HTTPException) as exc:
            normalize_phone(invalid, mobile=True)
        assert exc.value.status_code == 422


def test_account_identity_saves_both_international_phones(monkeypatch, fake_db):
    db = fake_db({"users": [{"id": "mine", "email": "mine@example.com"}], "account_billing_identity": []})
    monkeypatch.setattr(users_router, "get_supabase", lambda: db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "mine"
    try:
        result = TestClient(app).put("/users/me/identity", json={
            "mobile_phone": "+1 (415) 555-1234", "contact_phone": "+351 912 345 678",
        })
        assert result.status_code == 200
        assert result.json()["mobile_phone"] == "+14155551234"
        assert result.json()["contact_phone"] == "+351912345678"
        assert result.json()["purchase_readiness"]["missing"] == ["Nome e sobrenome", "CPF"]
    finally:
        app.dependency_overrides.clear()


def test_identity_api_requires_session():
    app.dependency_overrides.clear()
    client = TestClient(app)
    assert client.get("/users/me/identity").status_code == 401
    assert client.put("/users/me/identity", json={"full_name": "Cliente Teste"}).status_code == 401


def test_account_identity_ownership_and_no_raw_cpf(monkeypatch, fake_db):
    db = fake_db({
        "users": [
            {"id": "mine", "email": "mine@example.com"},
            {"id": "other", "email": "other@example.com"},
        ],
        "account_billing_identity": [{"user_id": "other", "full_name": "Outra Pessoa",
                                      "cpf_ciphertext": "secret-other", "mobile_phone": "21977777777"}],
    })
    monkeypatch.setattr(users_router, "get_supabase", lambda: db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "mine"
    try:
        client = TestClient(app)
        before = client.get("/users/me/identity")
        assert before.status_code == 200
        assert before.json()["purchase_readiness"]["ready"] is False
        assert "other@example.com" not in before.text
        created = client.put("/users/me/identity", json={
            "full_name": "Cliente Teste", "cpf": "52998224725", "mobile_phone": "(21) 99999-8888",
            "age": 29, "birth_date": "1988-05-17", "cep": "23000-000", "user_id": "other",
        })
        assert created.status_code == 200
        assert created.json()["purchase_readiness"] == {"ready": True, "missing": []}
        assert client.get("/users/me/purchase-readiness").json() == {"ready": True, "missing": []}
        assert created.json()["cpf_registered"] is True
        assert "52998224725" not in created.text
        saved = db.tables["account_billing_identity"][-1]
        assert saved["user_id"] == "mine"
        assert saved["cpf_ciphertext"] != "52998224725"
        assert saved["mobile_phone"] == "21999998888"
        assert saved["cep"] == "23000000"
        assert saved["birth_date"] == "1988-05-17"
        assert created.json()["birth_date"] == "1988-05-17"
        assert db.tables["account_billing_identity"][0]["user_id"] == "other"
        # Salvar outro campo não pode apagar o CPF já cifrado no banco.
        edited = client.put("/users/me/identity", json={"mobile_phone": "21999997777"})
        assert edited.status_code == 200
        assert edited.json()["cpf_registered"] is True
        assert edited.json()["purchase_readiness"]["ready"] is True
        assert db.tables["account_billing_identity"][-1]["cpf_ciphertext"] == saved["cpf_ciphertext"]
        assert edited.json()["birth_date"] == "1988-05-17"
    finally:
        app.dependency_overrides.clear()


def test_identity_api_rejects_invalid_cpf_before_write(monkeypatch, fake_db):
    db = fake_db({"users": [{"id": "mine", "email": "mine@example.com"}], "account_billing_identity": []})
    monkeypatch.setattr(users_router, "get_supabase", lambda: db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "mine"
    try:
        response = TestClient(app).put("/users/me/identity", json={
            "full_name": "Cliente Teste", "cpf": "11111111111",
        })
        assert response.status_code == 422
        assert db.tables["account_billing_identity"] == []
    finally:
        app.dependency_overrides.clear()


def test_identity_rejects_invalid_or_future_birth_date(monkeypatch, fake_db):
    db = fake_db({"users": [{"id": "mine", "email": "mine@example.com"}], "account_billing_identity": []})
    monkeypatch.setattr(users_router, "get_supabase", lambda: db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "mine"
    try:
        client = TestClient(app)
        for invalid in ("2035-01-01", "1988-02-30"):
            response = client.put("/users/me/identity", json={"birth_date": invalid})
            assert response.status_code == 422
        assert db.tables["account_billing_identity"] == []
    finally:
        app.dependency_overrides.clear()


def test_identity_first_access_when_maybe_single_returns_none(monkeypatch, fake_db):
    """Regressão real: postgrest-py devolve None se a conta ainda não tem cadastro."""
    db = fake_db({"users": [{"id": "mine", "email": "mine@example.com"}],
                  "account_billing_identity": []})
    original_table = db.table

    def table_with_nullable_single(name):
        query = original_table(name)
        original_execute = query.execute

        def execute():
            result = original_execute()
            if query._single and result.data is None:
                return None
            return result

        query.execute = execute
        return query

    monkeypatch.setattr(db, "table", table_with_nullable_single)
    monkeypatch.setattr(users_router, "get_supabase", lambda: db)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user_id] = lambda: "mine"
    try:
        client = TestClient(app)
        empty = client.get("/users/me/identity")
        assert empty.status_code == 200
        assert empty.json()["email"] == "mine@example.com"
        assert empty.json()["cpf_registered"] is False
        assert empty.json()["full_name"] is None
        assert empty.json()["purchase_readiness"]["ready"] is False
        assert client.get("/users/me/purchase-readiness").status_code == 200

        saved = client.put("/users/me/identity", json={
            "full_name": "Cliente Teste", "cpf": "52998224725", "mobile_phone": "21999998888",
        })
        assert saved.status_code == 200
        assert saved.json()["purchase_readiness"]["ready"] is True
        assert len(db.tables["account_billing_identity"]) == 1

        app.dependency_overrides[get_current_user_id] = lambda: "missing"
        assert client.get("/users/me/identity").status_code == 404
    finally:
        app.dependency_overrides.clear()
