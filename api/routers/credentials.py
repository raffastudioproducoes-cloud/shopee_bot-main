"""
Credenciais Router — API Python (FastAPI)

CRUD das credenciais de rede social/afiliado. Nunca retorna o valor
cifrado de volta ao cliente — só status (conectado/desconectado).

Shopee valida a credencial ao vivo contra a API deles antes de salvar
(igual o Flask sempre fez) — via web/routes/internal.py, porque
apis/shopee.py depende do alias de pacote shopee_bot.* que só existe
no processo Flask. Se a chamada interna falhar (Flask fora do ar, ou
FLASK_INTERNAL_URL/INTERNAL_API_SECRET não configurados), o save de
Shopee falha com 502 em vez de salvar sem validar — melhor recusar do
que gravar uma credencial nunca verificada.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import get_current_user_id
from ..database import supabase
from ..crypto import encrypt
from ..internal_client import validate_shopee_credential, InternalApiError

router = APIRouter(prefix="/credentials", tags=["credentials"])

# Redes com o mesmo formato de credencial: app_id + secret.
SIMPLE_NETWORKS = {
    "shopee": "shopee_credentials",
    "x": "x_credentials",
    "facebook": "facebook_credentials",
    "instagram": "instagram_credentials",
    "tiktok": "tiktok_credentials",
    "kwai": "kwai_credentials",
}


class SimpleCredentialBody(BaseModel):
    app_id: str
    secret: str


class ThreadsCredentialBody(BaseModel):
    t_user_id: str
    access_token: str


def _simple_table(network: str) -> str:
    table = SIMPLE_NETWORKS.get(network)
    if not table:
        raise HTTPException(status_code=404, detail=f"Rede '{network}' não suportada")
    return table


def _status_only(row: dict | None) -> dict:
    if not row:
        return {"connected": False}
    return {"connected": bool(row.get("status"))}


def _upsert_by_user(table: str, user_id: int, data: dict) -> dict:
    """update-or-insert por user_id. Não existe unique constraint em
    user_id nessas tabelas (só em app_id/t_user_id) — upsert nativo do
    Postgres via on_conflict não se aplica aqui."""
    existing = (
        supabase.table(table).select("id").eq("user_id", user_id)
        .maybe_single().execute()
    )
    if existing and existing.data:
        result = (
            supabase.table(table).update(data).eq("user_id", user_id).execute()
        )
    else:
        result = supabase.table(table).insert({**data, "user_id": user_id}).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao salvar credencial")
    return result.data[0]


@router.get("/")
async def list_credentials(user_id: int = Depends(get_current_user_id)):
    """Status de conexão (sem valor) de todas as redes suportadas."""
    result: dict[str, dict] = {}

    for network, table in SIMPLE_NETWORKS.items():
        row = (
            supabase.table(table).select("status").eq("user_id", user_id)
            .maybe_single().execute()
        )
        result[network] = _status_only(row.data if row else None)

    threads_row = (
        supabase.table("threads_credentials").select("status")
        .eq("user_id", user_id).maybe_single().execute()
    )
    result["threads"] = _status_only(threads_row.data if threads_row else None)

    return result


@router.put("/threads")
async def save_threads_credential(
    body: ThreadsCredentialBody,
    user_id: int = Depends(get_current_user_id),
):
    """Threads usa OAuth (token obtido via callback do Flask, não por
    formulário) — este endpoint só permite colar um token já emitido.

    Rota literal registrada ANTES de "/{network}": no Starlette, rotas
    casam na ordem de registro, e "/{network}" aceitaria "threads" como
    valor de path param se viesse primeiro, roubando esta requisição.
    """
    _upsert_by_user("threads_credentials", user_id, {
        "t_user_id": body.t_user_id,
        "access_token": encrypt(body.access_token),
        "status": True,
    })
    return {"connected": True}


@router.delete("/threads")
async def delete_threads_credential(user_id: int = Depends(get_current_user_id)):
    result = (
        supabase.table("threads_credentials")
        .update({"t_user_id": None, "access_token": None, "status": False})
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}


@router.put("/{network}")
async def save_credential(
    network: str,
    body: SimpleCredentialBody,
    user_id: int = Depends(get_current_user_id),
):
    """Cria ou atualiza a credencial (update-or-insert por user_id). Cifra o secret."""
    table = _simple_table(network)

    if network == "shopee":
        try:
            valid = await validate_shopee_credential(body.app_id, body.secret)
        except InternalApiError:
            raise HTTPException(
                status_code=502,
                detail="Não foi possível validar a credencial da Shopee agora. Tente novamente.",
            )
        if not valid:
            raise HTTPException(status_code=400, detail="Credencial da Shopee inválida")

    _upsert_by_user(table, user_id, {
        "app_id": body.app_id,
        "secret": encrypt(body.secret),
        "status": True,
    })
    return {"connected": True}


@router.delete("/{network}")
async def delete_credential(
    network: str,
    user_id: int = Depends(get_current_user_id),
):
    """Desconecta (zera app_id/secret, status=False) — não apaga a linha."""
    table = _simple_table(network)
    result = (
        supabase.table(table)
        .update({"app_id": None, "secret": None, "status": False})
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Credencial não encontrada")
    return {"connected": False}
