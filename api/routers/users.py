"""
Usuários Router — API Python (FastAPI)

CRUD administrativo de usuários. Só ADMIN acessa (mesma regra do
Flask: web/routes/users.py before_request).
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, ValidationError

from .auth import (
    _check_login_rate_limit,
    _validate_password_length,
    get_current_user_id,
    provision_new_user,
    pwd_context,
)
from .lists import _get_list_products, _sync_list_products
from .posts import _create_thread, _get_post_products, _get_thread_chain, _set_post_products
from .products import ProductCreate, _normalize_numeric_fields, find_product_in_account
from .profiles import get_current_profile_id
from ..audit_trail import record_audit_event
from ..config import settings
from ..database import supabase
from ..profiles import scope_account, scope_owner
from ..utils.log_sanitizer import sanitize_log_data

# Tetos de item por lista no restore (item 2 da revisão de segurança):
# sem isso, um backup com dezenas de milhares de itens insere um a um,
# de forma síncrona, dentro de uma rota `async def` — trava a event loop
# inteira do uvicorn e derruba todo mundo, não só quem restaura. Números
# generosos pro uso normal (poucas dezenas/centenas de produtos por
# conta), pequenos o bastante pra nunca virar problema de performance.
_MAX_BACKUP_PRODUCTS = 1000
_MAX_BACKUP_PRODUCT_LISTS = 200
_MAX_BACKUP_POSTS = 500
_MAX_BACKUP_TEXTS_PER_POST = 50

router = APIRouter(prefix="/users", tags=["users"])


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
    (POST /users/me/restore) — ver item 10.8 do backlog.

    Os 3 campos de lista ficam como `dict[str, Any]` (não tipados com o
    schema final) de propósito: o checksum é recalculado no restore sobre
    o payload exatamente como o client enviou (mesmo formato devolvido
    pelo export), então tipar aqui já forte demais faria o Pydantic
    descartar/normalizar campo ANTES do checksum ser conferido — quebraria
    o checksum de qualquer backup exportado antes dessa validação existir.
    A validação de formato (allowlist de campo, tipo, teto de item) roda
    manualmente dentro do loop do restore, depois da conferência do
    checksum (ver `_validate_backup_item` e `restore_backup`)."""

    products: list[dict[str, Any]] = Field(max_length=_MAX_BACKUP_PRODUCTS)
    product_lists: list[dict[str, Any]] = Field(max_length=_MAX_BACKUP_PRODUCT_LISTS)
    posts: list[dict[str, Any]] = Field(max_length=_MAX_BACKUP_POSTS)
    exported_at: str
    checksum: str


class _BackupProductList(BaseModel):
    """Item validado de `BackupData.product_lists` — usado só dentro do
    loop de restore (ver docstring de `BackupData`)."""

    name: str
    product_ids: list[Any] = Field(default_factory=list)


class _BackupPost(BaseModel):
    """Item validado de `BackupData.posts` — usado só dentro do loop de
    restore (ver docstring de `BackupData`)."""

    network: str | None = None
    texts: list[str] = Field(default_factory=list, max_length=_MAX_BACKUP_TEXTS_PER_POST)
    product_ids: list[Any] = Field(default_factory=list)


def _validate_backup_item(model: type[BaseModel], item: Any, label: str) -> BaseModel:
    """Valida um item solto (dict vindo de `list[dict[str, Any]]`) contra
    um schema Pydantic — allowlist de campo (schema já existente pra
    produto, `ProductCreate`) em vez de denylist, e 422 claro em vez de
    500 pra formato inválido (item malformado: não é dict, tipo errado,
    lista onde devia ser string etc — ver item 5 da revisão)."""
    if not isinstance(item, dict):
        raise HTTPException(
            status_code=422,
            detail=f"Item inválido em '{label}': esperado objeto, recebeu {type(item).__name__}.",
        )
    try:
        return model.model_validate(item)
    except ValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(part) for part in first_error["loc"])
        raise HTTPException(
            status_code=422,
            detail=f"Item inválido em '{label}' (campo '{field}'): {first_error['msg']}.",
        )


def _delete_user_row(user_id: str | int):
    """Exclui a linha em `users`. Compartilhado pelo DELETE admin e pela
    autoexclusão — não duplica a query de delete entre os dois endpoints.

    Cascata cuida das tabelas relacionadas (credenciais, produtos, listas,
    posts etc. — todas com FK `user_id` `ON DELETE CASCADE`, ver
    `database/migrations/`), então não há limpeza manual extra a fazer aqui.
    """
    return supabase.table("users").delete().eq("id", user_id).execute()


def _collect_backup_data(user_id: str, profile_id: str | None = None) -> dict[str, Any]:
    """Reúne os próprios dados do usuário (item 10.8 do backlog) — só os do
    perfil ativo quando houver. Sem perfil ativo, exporta apenas o catálogo
    compartilhado da conta — nunca listas/posts de outro perfil. Reusando
    as mesmas queries/helpers dos routers de produtos/listas/posts — nunca
    inclui mídia binária nem dado de agendamento (ver docstring de
    restore_backup sobre o porquê de agendamento ficar de fora)."""
    products_result = scope_account(supabase.table("products").select("*"), user_id).execute()
    products = [_normalize_numeric_fields(dict(row)) for row in (products_result.data or [])]

    product_lists = []
    posts = []
    if profile_id:
        lists_result = scope_owner(
            supabase.table("product_lists").select("*"), user_id, profile_id
        ).execute()
        for item in lists_result.data or []:
            list_products = _get_list_products(item["id"])
            product_lists.append({
                "name": item["name"],
                "product_ids": [p["id"] for p in list_products],
            })

        posts_result = (
            scope_owner(supabase.table("posts").select("*"), user_id, profile_id)
            .is_("post_id", "null").execute()
        )
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
    """HMAC-SHA256 (chave: `api_secret_key`, mesmo segredo que já assina
    o JWT — não existe outro no `api/config.py`) sobre os dados JÁ
    sanitizados (defesa em profundidade, ver docstring de
    log_sanitizer.py; `mask_value_patterns=False` — ver docstring do
    parâmetro), chaves ordenadas. Mesma função usada no export (calcula)
    e no restore (recalcula pra comparar) — garante que os dois lados
    sempre concordam.

    Antes era SHA-256 puro: qualquer um edita o JSON e recalcula o hash
    igual, então "checksum" não provava nada além de corrupção acidental
    (a docstring de `restore_backup` promete proteção contra "arquivo
    adulterado" — só HMAC com segredo do servidor entrega isso de
    verdade, por isso a troca)."""
    sanitized = sanitize_log_data(data, mask_value_patterns=False)
    serialized = json.dumps(sanitized, sort_keys=True, ensure_ascii=False, default=str)
    return hmac.new(
        settings.api_secret_key.encode("utf-8"),
        serialized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _require_admin(user_id: str = Depends(get_current_user_id)) -> int:
    result = (
        supabase.table("users").select("access").eq("id", user_id)
        .maybe_single().execute()
    )
    # maybe_single: linha inexistente vira 403, não 500 (.single() levanta
    # e o supabase-py devolve None em vez de resposta vazia).
    if not result or not result.data or result.data.get("access") != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user_id


@router.get("")
async def list_users(
    _admin_id: str = Depends(_require_admin),
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
async def create_user(body: UserCreate, _admin_id: str = Depends(_require_admin)):
    if body.access not in ("USER", "ADMIN"):
        raise HTTPException(status_code=400, detail="access deve ser USER ou ADMIN")

    _validate_password_length(body.password)

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

    # Credenciais vazias por rede (padrão do Flask, web/routes/users.py) +
    # perfil principal, igual a /auth/register; desfaz o usuário se falhar.
    provision_new_user(supabase, result.data[0])

    return result.data[0]


@router.delete("/me")
async def delete_own_account(
    body: SelfDeleteRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
):
    """Autoexclusão de conta e dados (LGPD/direito ao esquecimento).

    Exige a senha atual — ação irreversível, cookie de sessão sozinho não é
    prova de posse suficiente (mesmo padrão do reset de senha em auth.py).
    Rate-limitada (mesmo mecanismo de `/auth/login`) — sem isso alguém com
    cookie roubado podia tentar adivinhar a senha atual sem limite (bcrypt
    só atrasa, não impede).
    """
    _check_login_rate_limit(f"selfdelete:{user_id}")

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
        # Sem username aqui: dado pessoal não precisa sobreviver ao
        # "direito ao esquecimento" que este próprio evento representa
        # (entity_id já carrega o id, suficiente pra rastrear a exclusão).
        old_value={"id": str(user_id), "access": current.data.get("access")},
        new_value=None,
    )

    # Mesmo mecanismo do /auth/logout — sem isso a sessão continuaria
    # "válida" (JWT ainda não expirado) para uma conta que não existe mais.
    response.delete_cookie(key="access_token")

    return {"msg": "Conta removida"}


@router.get("/me/backup")
async def export_backup(
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Exporta produtos/listas/posts do PRÓPRIO usuário com checksum de
    integridade (item 10.8 do backlog). Nunca inclui senha/token/segredo
    (sanitize_log_data aplicado antes do checksum, mesmo já não devendo
    haver nada sensível nesses três recortes de dado)."""
    _check_login_rate_limit(f"backup:{user_id}")
    data = _collect_backup_data(user_id, profile_id)
    # mask_value_patterns=False: dado do próprio dono (não é log público),
    # e o detector de padrão por valor estragava URL legítima com
    # "?token=" na query string (ver docstring do parâmetro).
    sanitized = sanitize_log_data(data, mask_value_patterns=False)
    return {**sanitized, "checksum": _checksum(data)}


@router.post("/me/restore")
def restore_backup(
    body: BackupData,
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    """Importa um backup gerado por export_backup. Rejeita com 400 (e não
    importa nada) se o checksum não bater — arquivo adulterado/corrompido
    (comparação com `hmac.compare_digest`, constante no tempo).

    Restore é ADITIVO: sempre cria registros novos (nunca sobrescreve ou
    apaga dado existente do usuário) — política mais simples e mais segura
    pro MVP (YAGNI: sem merge inteligente). EXCEÇÃO: produto cujo
    `(product_id, perfil ativo)` já existe (restaurar na própria conta que
    gerou o backup — o uso normal de "conferir/restaurar") atualiza
    o produto existente em vez de estourar a constraint única
    e derrubar a requisição inteira com 500 no meio da inserção (deixando
    o que já foi inserido antes órfão). `user_id` do backup nunca é
    usado — tudo é recriado sob o usuário autenticado da sessão atual e,
    quando há perfil ativo, sob esse perfil (o backup antigo, sem
    `profile_id`, continua válido: o campo nunca vem do arquivo). O mesmo
    produto pode existir em perfis diferentes (migração 041): o de outro
    perfil nunca é tocado, o restore cria/atualiza o do perfil ativo.

    Cada item de `products`/`product_lists`/`posts` é validado (allowlist
    de campo — `ProductCreate`, mesmo schema já usado pra criar produto —
    e tipo) antes de tocar o banco; item malformado vira 422 com o campo
    exato, nunca um 500 (ver `_validate_backup_item`). Listas em si têm
    teto de tamanho (`BackupData`) — protege contra um backup com dezenas
    de milhares de itens travando a event loop do uvicorn: a rota agora é
    `def` (não `async def`), então o FastAPI roda o corpo inteiro numa
    threadpool, sem bloquear outras requisições enquanto os inserts
    síncronos do Supabase rodam um a um.

    Agendamento de post fica de fora de propósito: reagendar exigiria
    chamar o bridge do scheduler (`api/internal_client.py`) para cada
    post restaurado, o que acopla restore a um serviço externo (Flask)
    só pra recriar automação, não dado — fora do escopo de "backup de
    dados". Post restaurado volta sem agendamento ativo."""
    _check_login_rate_limit(f"restore:{user_id}")
    payload = {
        "products": body.products,
        "product_lists": body.product_lists,
        "posts": body.posts,
        "exported_at": body.exported_at,
    }
    if not hmac.compare_digest(_checksum(payload), body.checksum):
        raise HTTPException(status_code=400, detail="Arquivo de backup corrompido ou inválido.")
    if (body.product_lists or body.posts) and not profile_id:
        raise HTTPException(status_code=400, detail="Perfil ativo obrigatório para restaurar listas ou posts.")

    id_map: dict[Any, int] = {}
    for product in body.products:
        validated = _validate_backup_item(ProductCreate, product, "products")
        new_row = validated.model_dump()
        new_row["user_id"] = user_id
        # Sem on_conflict: procura o produto compartilhado da conta e atualiza/cria.
        existing = find_product_in_account(supabase, user_id, new_row["product_id"])
        if existing:
            result = supabase.table("products").update(new_row).eq("id", existing["id"]).execute()
        else:
            result = supabase.table("products").insert(new_row).execute()
        if result.data:
            id_map[product.get("id")] = result.data[0]["id"]

    for plist in body.product_lists:
        validated_list = _validate_backup_item(_BackupProductList, plist, "product_lists")
        result = (
            supabase.table("product_lists")
            .insert({
                "user_id": user_id, "name": validated_list.name,
                "profile_id": profile_id,
            })
            .execute()
        )
        if not result.data:
            continue
        new_product_ids = [
            id_map[pid] for pid in validated_list.product_ids if pid in id_map
        ]
        if new_product_ids:
            _sync_list_products(user_id, result.data[0]["id"], new_product_ids)

    for post in body.posts:
        validated_post = _validate_backup_item(_BackupPost, post, "posts")
        if not validated_post.texts:
            continue
        head = _create_thread(
            user_id, validated_post.texts, validated_post.network or "threads", profile_id
        )
        new_product_ids = [
            id_map[pid] for pid in validated_post.product_ids if pid in id_map
        ]
        if new_product_ids:
            _set_post_products(head["id"], new_product_ids)

    return {"msg": "Backup restaurado com sucesso"}


@router.get("/{user_id}")
async def get_user(user_id: str, _admin_id: str = Depends(_require_admin)):
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
    _admin_id: str = Depends(_require_admin),
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
async def delete_user(user_id: str, _admin_id: str = Depends(_require_admin)):
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
        # Idem autoexclusão acima: sem username, id já está em entity_id.
        old_value={"id": str(user_id), "access": current.data.get("access")},
        new_value=None,
    )

    return {"msg": "Usuário removido"}
