"""Reserva atomica de espaco global no Storage Free, sem cota por usuario.

O projeto Supabase e compartilhado entre staging/main. A RPC utiliza lock
transacional do Postgres e reserva temporaria para contabilizar uploads em voo.
Falha ao consultar quota = falha fechada (503), sem gravar arquivos sem protecao.
"""
import logging
from contextlib import contextmanager
from uuid import UUID

from fastapi import HTTPException

from .database import supabase

logger = logging.getLogger("uvicorn.error")


@contextmanager
def storage_upload_reservation(size_bytes: int):
    """Serializa a reserva global, libera apos upload e expira apos 30 min."""
    if size_bytes <= 0 or size_bytes > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite permitido.")
    try:
        result = supabase.rpc(
            "reserve_storage_upload", {"p_size_bytes": size_bytes}
        ).execute()
        decision = result.data
        if not isinstance(decision, dict) or not isinstance(decision.get("allowed"), bool):
            raise ValueError("invalid_storage_reservation_response")
    except Exception as exc:
        logger.warning("Reserva de Storage indisponivel (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel verificar o espaco de arquivos. Tente novamente.",
        ) from None
    if not decision["allowed"]:
        if decision.get("reason") == "capacity_reached":
            raise HTTPException(
                status_code=507,
                detail="Armazenamento temporariamente no limite preventivo do plano Free. Nenhum arquivo foi enviado.",
            )
        raise HTTPException(status_code=413, detail="Tamanho de arquivo nao permitido.")
    try:
        reservation_id = str(UUID(str(decision["reservation_id"])))
    except (KeyError, ValueError, TypeError, AttributeError):
        logger.warning("Reserva de Storage sem identificador valido")
        raise HTTPException(
            status_code=503, detail="Nao foi possivel reservar espaco para o arquivo.",
        ) from None
    try:
        yield
    finally:
        try:
            supabase.rpc(
                "release_storage_upload", {"p_reservation_id": reservation_id}
            ).execute()
        except Exception as exc:
            # Reserva vence automaticamente no banco; nunca mascarar falha do upload.
            logger.warning("Liberacao de reserva de Storage pendente (%s)", type(exc).__name__)
