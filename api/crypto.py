"""
Cifra/decifra credenciais pra API nova.

Mesma chave e mesmo algoritmo do Flask (`utils/crypto.py`, Fernet padrão —
formato interoperável não importa qual módulo chama `Fernet(key).encrypt()`,
só a chave precisa ser igual). Não reusa `utils.crypto` diretamente: esse
pacote arrasta `requests`/`flask`/`pillow` (dependências do Flask alheias à
cifra em si) só pra rodar `utils/__init__.py`, o que infla `api/requirements.txt`
com deps que a API nova não precisa.

Sem suporte a rotação de chave aqui (utils/crypto.py tem `rotate_decrypt`) —
a API nova só cifra o que ela mesma grava; ler credencial gravada com chave
antiga continua tarefa do Flask.
"""

import os
from functools import lru_cache

from cryptography.fernet import Fernet


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(os.environ["APP_ENCRYPTION_KEY"].encode("ascii"))


def encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
