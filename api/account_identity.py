"""Identidade cadastral da CONTA, separada dos perfis sociais.

CPF é cifrado em repouso; apenas um HMAC determinístico (com chave secreta)
permite impedir duplicidades sem guardar o documento em claro. Nenhuma rota
retorna CPF completo nem dados de outra conta.
"""

import base64
import hashlib
import hmac
import os
import re

from fastapi import HTTPException

from .crypto import encrypt


def normalize_full_name(value: str) -> str:
    name = " ".join(value.strip().split())
    parts = name.split(" ")
    if not 5 <= len(name) <= 150 or len(parts) < 2 or any(len(part) < 2 for part in parts):
        raise HTTPException(422, "Informe nome e sobrenome completos.")
    if any(char.isdigit() for char in name):
        raise HTTPException(422, "O nome não pode conter números.")
    return name


def normalize_cpf(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 11 or len(set(digits)) == 1:
        raise HTTPException(422, "CPF inválido.")
    for end in (9, 10):
        check = (sum(int(d) * (end + 1 - i) for i, d in enumerate(digits[:end])) * 10) % 11
        if (check if check < 10 else 0) != int(digits[end]):
            raise HTTPException(422, "CPF inválido.")
    return digits


def cpf_record(value: str) -> dict[str, str]:
    cpf = normalize_cpf(value)
    # Mesma chave de cifragem Fernet configurada no servidor; não sai em JSON.
    secret = base64.urlsafe_b64decode(os.environ["APP_ENCRYPTION_KEY"].encode("ascii"))
    digest = hmac.new(secret, ("account-cpf-v1:" + cpf).encode(), hashlib.sha256).hexdigest()
    return {"cpf_ciphertext": encrypt(cpf), "cpf_fingerprint": digest}


def normalize_phone(value: str | None, *, mobile: bool = False) -> str | None:
    if not value or not value.strip():
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) not in ((11,) if mobile else (10, 11)) or digits[0] == "0" or digits[1] == "0":
        raise HTTPException(422, "Informe um telefone brasileiro com DDD válido.")
    if mobile and digits[2] != "9":
        raise HTTPException(422, "Celular deve ter DDD e nove dígitos, começando por 9.")
    return digits


def normalize_cep(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        raise HTTPException(422, "CEP deve conter oito dígitos.")
    return digits


def purchase_readiness(user: dict, identity: dict | None) -> dict:
    record = identity or {}
    missing = []
    if not record.get("full_name"):
        missing.append("Nome e sobrenome")
    if not record.get("cpf_ciphertext"):
        missing.append("CPF")
    if not user.get("email"):
        missing.append("E-mail")
    if not record.get("mobile_phone"):
        missing.append("Celular")
    return {"ready": not missing, "missing": missing}
