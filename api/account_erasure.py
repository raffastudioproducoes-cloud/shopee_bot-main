"""Apagamento integral e retomável de conta, sem novo cron.

O Supabase é compartilhado entre staging/main. Este módulo só inicia uma
operação se ACCOUNT_ERASURE_ENABLED=true. O banco coordena fases e retém
estado em account_erasure_tasks até a conclusão verificada.

Nunca remover storage.objects via SQL: deletar arquivos só pela Storage API.
Nenhuma exceção interna (Auth/Storage/PostgREST) deve chegar ao cliente.
"""
import logging
import os
from collections import defaultdict

from .config import settings
from .database import supabase

logger = logging.getLogger("uvicorn.error")
_MAX_STORAGE_BATCH = 100
_MAX_STORAGE_ROUNDS = 1000


def account_erasure_enabled() -> bool:
    return os.getenv("ACCOUNT_ERASURE_ENABLED", "false").lower() == "true"


def _rpc_json(name: str, user_id: str, *, extra: dict | None = None):
    params = {"p_user_id": str(user_id), **(extra or {})}
    result = supabase.rpc(name, params).execute()
    return result.data


def _delete_owned_storage(user_id: str) -> None:
    """Lê manifesto da conta via RPC service_role, apaga lotes, relê até vazio.

    Não usa offset: objetos removidos saem do topo. Verificação posterior no
    Postgres evita considerar uma resposta HTTP parcial como sucesso.
    """
    last_batch = None
    stagnant = 0
    for _ in range(_MAX_STORAGE_ROUNDS):
        rows = _rpc_json(
            "account_erasure_storage_manifest", user_id,
            extra={"p_limit": _MAX_STORAGE_BATCH},
        )
        if not isinstance(rows, list):
            raise RuntimeError("invalid_storage_manifest")
        if not rows:
            return
        by_bucket: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError("invalid_storage_manifest_item")
            bucket, key = row.get("bucket_id"), row.get("object_name")
            if bucket not in {"post-media", "avatars"} or not isinstance(key, str) or not key:
                raise RuntimeError("invalid_storage_manifest_scope")
            by_bucket[bucket].append(key)
        current = tuple((b, tuple(keys)) for b, keys in sorted(by_bucket.items()))
        if current == last_batch:
            stagnant += 1
            if stagnant >= 2:
                raise RuntimeError("storage_removal_not_progressing")
        else:
            stagnant = 0
        last_batch = current
        for bucket, keys in by_bucket.items():
            supabase.storage.from_(bucket).remove(keys)
    raise RuntimeError("storage_erasure_batch_limit")


def _remove_auth_identity(auth_user_id: str | None) -> None:
    if not auth_user_id:
        return
    try:
        supabase.auth.admin.delete_user(str(auth_user_id))
    except Exception as exc:
        # Reexecução idempotente: pode ter sido removida na tentativa anterior.
        status = getattr(exc, "status_code", getattr(exc, "status", None))
        if str(status) != "404":
            raise


def erase_account(user_id: str) -> dict:
    """Operação explicitamente irreversível; exige confirmação no endpoint.

    Início cancela despacho e marca usuário em exclusão. Falha posterior não
    elimina o estado de recuperação; admin pode retomar com mesmo user_id.
    """
    if not account_erasure_enabled():
        raise RuntimeError("account_erasure_disabled")
    begin = _rpc_json("begin_account_erasure", user_id)
    if not isinstance(begin, dict) or str(begin.get("user_id")) != str(user_id):
        raise RuntimeError("invalid_erasure_begin")
    _delete_owned_storage(user_id)
    if _rpc_json("mark_account_erasure_storage_complete", user_id) is not True:
        raise RuntimeError("invalid_storage_completion")
    _remove_auth_identity(begin.get("auth_user_id"))
    if _rpc_json("mark_account_erasure_auth_complete", user_id) is not True:
        raise RuntimeError("invalid_auth_completion")
    finished = _rpc_json("finalize_account_erasure", user_id)
    if not isinstance(finished, dict) or finished.get("status") != "deleted":
        raise RuntimeError("invalid_erasure_completion")
    return finished
