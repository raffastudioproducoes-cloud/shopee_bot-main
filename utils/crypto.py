import os
from cryptography.fernet import Fernet, InvalidToken

_current_fernet = None
_current_key_id = None

# Key rotation support: geral um ID de chave a partir do hash da chave atual.
# Quando trocar a chave no .env, o ID muda e o sistema sabe que precisa
# migrar os dados cifrados pela chave antiga. A rotação é manual:
#   1. Gerar nova chave: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   2. Atualizar APP_ENCRYPTION_KEY no .env
#   3. Rodar o script de re-cifragem (one-shot) passando a chave antiga como argumento
#      ou via variável de ambiente APP_ENCRYPTION_KEY_OLD.


def _key_id_from_bytes(key_bytes: bytes) -> str:
    """Retorna um identificador curto e estável para uma chave Fernet."""
    import hashlib
    digest = hashlib.sha256(key_bytes).hexdigest()
    return digest[:12]


def _get_fernet():
    global _current_fernet, _current_key_id
    if _current_fernet is None:
        raw = os.environ["APP_ENCRYPTION_KEY"]
        key_bytes = raw.encode("ascii")
        _current_fernet = Fernet(key_bytes)
        _current_key_id = _key_id_from_bytes(key_bytes)
    return _current_fernet, _current_key_id


def encrypt(value: str | None) -> str | None:
    """Cifra uma string para guardar em coluna de credencial no banco.

    O valor retornado é o token Fernet como string ASCII.
    """
    if value is None:
        return None
    fernet, _ = _get_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str | None) -> str | None:
    """Decifra um valor lido do banco. None passa direto.

    Levanta InvalidToken se o valor não foi cifrado com a chave atual
    (ex.: dado legado em texto puro, ou cifrado com chave antiga) — não
    mascara o erro, porque devolver a credencial errada silenciosamente é
    pior que falhar.
    """
    if value is None:
        return None
    fernet, _ = _get_fernet()
    return fernet.decrypt(value.encode("ascii")).decode("utf-8")


def current_key_id() -> str:
    """Retorna o ID da chave Fernet atualmente em uso.

    Útil para logging/ auditing: saber qual chave cifrou cada registro
    ajuda a decidir quando a rotação é necessária e a mensurar o progresso
    da migração.
    """
    _, kid = _get_fernet()
    return kid


def rotate_decrypt(stale_value: str | None, old_key: str | None = None) -> str | None:
    """Decifra com a chave antiga durante a rotação de chaves.

    Args:
        stale_value: valor cifrado com uma chave que não é mais a ativa.
        old_key: a chave antiga (APP_ENCRYPTION_KEY anterior), opcional.
            Se não informada, usa APP_ENCRYPTION_KEY_OLD do .env.

    Retorna o texto claro ou None se o valor for None.

    Levanta InvalidToken se a chave for incorreta ou o dado não for um
    token Fernet válido.
    """
    if stale_value is None:
        return None
    if old_key is None:
        old_key = os.environ.get("APP_ENCRYPTION_KEY_OLD")
    if not old_key:
        raise ValueError(
            "rotate_decrypt requer old_key (APP_ENCRYPTION_KEY anterior) "
            "ou a variável de ambiente APP_ENCRYPTION_KEY_OLD"
        )
    fernet = Fernet(old_key.encode("ascii"))
    return fernet.decrypt(stale_value.encode("ascii")).decode("utf-8")
