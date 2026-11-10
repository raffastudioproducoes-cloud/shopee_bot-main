"""Verificação de senha vazada (S-05) por k-anonimato, sem custo e sem enviar a senha.

Usa a API de intervalos do Have I Been Pwned: só os **5 primeiros caracteres do SHA-1** da senha saem
do servidor; a comparação do restante é feita aqui. Nenhuma senha, hash completo, e-mail ou dado da
conta é enviado. `Add-Padding` impede inferir o tamanho da resposta.

Se o serviço estiver fora do ar ou lento (timeout de 3 s), a verificação **não bloqueia** o cadastro
(falha aberta, com aviso no log): a segurança principal continua sendo o tamanho mínimo e o Supabase Auth.
"""
import asyncio
import hashlib
import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

HIBP_RANGE_URL = "https://api.pwnedpasswords.com/range/"
TIMEOUT_SECONDS = 3.0
DETAIL = "Esta senha apareceu em vazamentos de dados conhecidos. Escolha outra senha, que você não use em outros sites."


def _sha1_parts(password: str) -> tuple[str, str]:
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    return digest[:5], digest[5:]


def breach_count(password: str) -> int | None:
    """Quantas vezes a senha aparece em vazamentos; None se não foi possível consultar."""
    prefix, suffix = _sha1_parts(password)
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as http:
            response = http.get(HIBP_RANGE_URL + prefix, headers={"Add-Padding": "true"})
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Verificação de senha vazada indisponível; seguindo sem bloquear")
        return None
    for line in response.text.splitlines():
        candidate, _, count = line.partition(":")
        if candidate.strip().upper() == suffix:
            try:
                return int(count.strip())
            except ValueError:
                return 1
    return 0


async def ensure_password_not_breached(password: str) -> None:
    """Recusa (422) senha presente em vazamentos conhecidos. Nunca registra a senha."""
    count = await asyncio.to_thread(breach_count, password)
    if count:
        raise HTTPException(status_code=422, detail=DETAIL)
