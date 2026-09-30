"""
Usuários Router — API Python (FastAPI)

CRUD administrativo de usuários. Só ADMIN acessa (mesma regra do
Flask: web/routes/users.py before_request).
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from .auth import get_current_user_id
from .lists import _get_list_products, _sync_list_products
from .posts import _create_thread, _get_post_products, _get_thread_chain, _set_post_products
from .products import _normalize_numeric_fields
from ..audit_trail import record_audit_event
from ..database import supabase
from ..utils.log_sanitizer import sanitize_log_data

router = APIRouter(prefix="/users", tags=["users"])

NETWORK_TABLES = [
    "shopee_credentials",
    "threads_credentials",
    "x_credentials",
    "facebook_credentials",
    "instagram_credentials",
    "tiktok_credentials",
    "kwai_credentials",
]


class UserCreate(BaseModel):
    username: str
    password: str
    access: str = "USER"


class UserUpdate(BaseModel):
    username: str
    access: str


class SelfDeleteRequest(BaseModel):
    current_password: str


class BackupData(BaseModel):
    """Formato compartilhado por export (GET /users/me/backup) e import
    (POST /users/me/restore) — ver item 10.8 do backlog."""

    products: list[dict[str, Any]]
    product_lists: list[dict[str, Any]]
    posts: list[dict[str, Any]]
    exported_at: str
    checksum: str


def _delete_user_row(user_id: str | int):
    """Exclui a linha em `users`. Compartilhado pelo DELETE admin e pela
    autoexclusão — não duplica a query de delete entre os dois endpoints.

    Cascata cuida das tabelas relacionadas (credenciais, produtos, listas,
    posts etc. — todas com FK `user_id` `ON DELETE CASCADE`, ver
    `database/migrations/`), então não há limpeza manual extra a fazer aqui.
    """
    return supabase.table("users").delete().eq("id", user_id).execute()


def _collect_backup_data(user_id: int) -> dict[str, Any]:
    """Reúne os próprios dados do usuário (item 10.8 do backlog) reusando
    as mesmas queries/helpers dos routers de produtos/listas/posts — nunca
    inclui mídia binária nem dado de agendamento (ver docstring de
    restore_backup sobre o porquê de agendamento ficar de fora)."""
    products_result = supabase.table("products").select("*").eq("user_id", user_id).execute()
    products = [_normalize_numeric_fields(dict(row)) for row in (products_result.data or [])]

    lists_result = supabase.table("product_lists").select("*").eq("user_id", user_id).execute()
    product_lists = []
    for item in lists_result.data or []:
        list_products = _get_list_products(item["id"])
        product_lists.append({
            "name": item["name"],
            "product_ids": [p["id"] for p in list_products],
        })

    posts_result = (
        supabase.table("posts").select("*")
        .eq("user_id", user_id).is_("post_id", "null").execute()
    )
    posts = []
    for item in posts_result.data or []:
        chain = _get_thread_chain(item["id"])
        posts.append({
            "network": item.get("network"),
            "texts": [row["text"] for row in chain],
            "product_ids": [p["id"] for p in _get_post_products(item["id"])],
        })

    return {
        "products": products,
        "product_lists": product_lists,
        "posts": posts,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


def _checksum(data: dict[str, Any]) -> str:
    """SHA-256 determinístico sobre os dados JÁ sanitizados (defesa em
    profundidade, ver docstring de log_sanitizer.py), chaves ordenadas.
    Mesma função usada no export (calcula) e no restore (recalcula pra
    comparar) — garante que os dois lados sempre concordam."""
    sanitized = sanitize_log_data(data)
    serialized = json.dumps(sanitized, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _require_admin(user_id: int = Depends(get_current_user_id)) -> int:
    result = (
        supabase.table("users").select("access").eq("id", user_id)
        .single().execute()
    )
    if not result.data or result.data.get("access") != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user_id


@router.get("")
async def list_users(
    _admin_id: int = Depends(_require_admin),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    query = (
        supabase.table("users")
        .select("id, username, access, created_at, updated_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)
    result = query.execute()

    next_cursor = None
    if result.data and len(result.data) == limit:
        next_cursor = result.data[-1]["created_at"]

    return {"data": result.data, "next_cursor": next_cursor}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, _admin_id: int = Depends(_require_admin)):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    if body.access not in ("USER", "ADMIN"):
        raise HTTPException(status_code=400, detail="access deve ser USER ou ADMIN")

    if body.username.lower() == "rafastudio":
        # Mesmo motivo do register() em auth.py: bloqueia squatting do
        # username reservado da conta master-admin.
        raise HTTPException(status_code=409, detail="Nome de usuário já existe")

    result = (
        supabase.table("users")
        .insert({
            "username": body.username,
            "password": pwd_context.hash(body.password),
            "access": body.access,
        })
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Falha ao criar usuário")

    new_user_id = result.data[0]["id"]

    # Semeia uma linha vazia de credencial por rede — mesmo padrão do
    # Flask (web/routes/users.py) para a tela de credenciais sempre
    # ter uma linha pra cada rede, independente de já ter conectado.
    for table in NETWORK_TABLES:
        supabase.table(table).insert({"user_id": new_user_id, "status": False}).execute()

    return result.data[0]


@router.delete("/me")
async def delete_own_account(
    body: SelfDeleteRequest,
    response: Response,
    user_id: int = Depends(get_current_user_id),
):
    """Autoexclusão de conta e dados (LGPD/direito ao esquecimento).

    Exige a senha atual — ação irreversível, cookie de sessão sozinho não é
    prova de posse suficiente (mesmo padrão do reset de senha em auth.py).
    """
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    current = (
        supabase.table("users").select("username, access, password").eq("id", user_id)
        .single().execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not pwd_context.verify(body.current_password, current.data.get("password", "")):
        raise HTTPException(status_code=403, detail="Senha atual incorreta")

    if current.data.get("username", "").lower() == "rafastudio":
        raise HTTPException(status_code=403, detail="Esta conta não pode ser removida")

    _delete_user_row(user_id)

    record_audit_event(
        entity="user",
        entity_id=str(user_id),
        user_id=str(user_id),
        action="user_self_deleted",
        old_value={"username": current.data.get("username"), "access": current.data.get("access")},
        new_value=None,
    )

    # Mesmo mecanismo do /auth/logout — sem isso a sessão continuaria
    # "válida" (JWT ainda não expirado) para uma conta que não existe mais.
    response.delete_cookie(key="access_token")

    return {"msg": "Conta removida"}


@router.get("/me/backup")
async def export_backup(user_id: int = Depends(get_current_user_id)):
    """Exporta produtos/listas/posts do PRÓPRIO usuário com checksum de
    integridade (item 10.8 do backlog). Nunca inclui senha/token/segredo
    (sanitize_log_data aplicado antes do checksum, mesmo já não devendo
    haver nada sensível nesses três recortes de dado)."""
    data = _collect_backup_data(user_id)
    sanitized = sanitize_log_data(data)
    return {**sanitized, "checksum": _checksum(data)}


@router.post("/me/restore")
async def restore_backup(body: BackupData, user_id: int = Depends(get_current_user_id)):
    """Importa um backup gerado por export_backup. Rejeita com 400 (e não
    importa nada) se o checksum não bater — arquivo adulterado/corrompido.

    Restore é ADITIVO: sempre cria registros novos (nunca sobrescreve ou
    apaga dado existente do usuário) — política mais simples e mais segura
    pro MVP (YAGNI: sem merge inteligente). `user_id` do backup nunca é
    usado — tudo é recriado sob o usuário autenticado da sessão atual.

    Agendamento de post fica de fora de propósito: reagendar exigiria
    chamar o bridge do scheduler (`api/internal_client.py`) para cada
    post restaurado, o que acopla restore a um serviço externo (Flask)
    só pra recriar automação, não dado — fora do escopo de "backup de
    dados". Post restaurado volta sem agendamento ativo."""
    payload = {
        "products": body.products,
        "product_lists": body.product_lists,
        "posts": body.posts,
        "exported_at": body.exported_at,
    }
    if _checksum(payload) != body.checksum:
        raise HTTPException(status_code=400, detail="Arquivo de backup corrompido ou inválido.")

    id_map: dict[Any, int] = {}
    for product in body.products:
        new_row = {
            key: value
            for key, value in product.items()
            if key not in ("id", "user_id", "created_at", "updated_at")
        }
        new_row["user_id"] = user_id
        result = supabase.table("products").insert(new_row).execute()
        if result.data:
            id_map[product.get("id")] = result.data[0]["id"]

    for plist in body.product_lists:
        result = (
            supabase.table("product_lists")
            .insert({"user_id": user_id, "name": plist.get("name")})
            .execute()
        )
        if not result.data:
            continue
        new_product_ids = [
            id_map[pid] for pid in plist.get("product_ids", []) if pid in id_map
        ]
        if new_product_ids:
            _sync_list_products(user_id, result.data[0]["id"], new_product_ids)

    for post in body.posts:
        texts = post.get("texts") or []
        if not texts:
            continue
        head = _create_thread(user_id, texts, post.get("network") or "threads")
        new_product_ids = [
            id_map[pid] for pid in post.get("product_ids", []) if pid in id_map
        ]
        if new_product_ids:
            _set_post_products(head["id"], new_product_ids)

    return {"msg": "Backup restaurado com sucesso"}


@router.get("/{user_id}")
async def get_user(user_id: str, _admin_id: int = Depends(_require_admin)):
    result = (
        supabase.table("users")
        .select("id, username, access, created_at, updated_at")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return result.data


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    _admin_id: int = Depends(_require_admin),
):
    if body.access not in ("USER", "ADMIN"):
        raise HTTPException(status_code=400, detail="access deve ser USER ou ADMIN")

    current = (
        supabase.table("users").select("username, access").eq("id", user_id)
        .single().execute()
    )
    if current.data and current.data.get("username", "").lower() == "rafastudio":
        if body.access != "ADMIN":
            raise HTTPException(status_code=403, detail="Esta conta deve permanecer ADMIN")
        if body.username != current.data.get("username"):
            raise HTTPException(status_code=403, detail="Esta conta não pode ser renomeada")

    result = (
        supabase.table("users")
        .update({"username": body.username, "access": body.access})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return result.data[0]


@router.delete("/{user_id}")
async def delete_user(user_id: str, _admin_id: int = Depends(_require_admin)):
    current = (
        supabase.table("users").select("username, access").eq("id", user_id)
        .single().execute()
    )
    if current.data and current.data.get("username", "").lower() == "rafastudio":
        raise HTTPException(status_code=403, detail="Esta conta não pode ser removida")

    result = _delete_user_row(user_id)
    if not result.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    record_audit_event(
        entity="user",
        entity_id=str(user_id),
        user_id=str(_admin_id),
        action="user_deleted",
        old_value=current.data,
        new_value=None,
    )

    return {"msg": "Usuário removido"}
