import os
from cryptography.fernet import Fernet, InvalidToken

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        key = os.environ["APP_ENCRYPTION_KEY"]
        _fernet = Fernet(key.encode("ascii"))
    return _fernet


def encrypt(value):
    """Cifra uma string pra guardar em coluna de credencial no banco."""
    if value is None:
        return None
    return _get_fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value):
    """Decifra um valor lido do banco. None passa direto.

    Levanta InvalidToken se o valor não foi cifrado com a chave atual
    (ex.: dado legado em texto puro) — não mascara o erro, porque
    devolver a credencial errada silenciosamente é pior que falhar.
    """
    if value is None:
        return None
    return _get_fernet().decrypt(value.encode("ascii")).decode("utf-8")
