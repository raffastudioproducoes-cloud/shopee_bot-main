"""
Usuários Router — API Python (FastAPI)

CRUD administrativo de usuários. Só ADMIN acessa (mesma regra do
Flask: web/routes/users.py before_request).
"""

import hashlib
import hmac
import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from starlette.concurrency import run_in_threadpool
from supabase import create_client
from pydantic import BaseModel, Field, ValidationError

from ..account_identity import (
    cpf_record, normalize_cep, normalize_full_name, normalize_phone, purchase_readiness,
)

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
from ..database import get_supabase, supabase
from ..account_erasure import erase_account, account_erasure_enabled
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


class AccountIdentityUpdate(BaseModel):
    """Dados da conta comercial, não dos perfis sociais da mesma conta."""

    full_name: str | None = Field(default=None, max_length=150)
    cpf: str | None = Field(default=None, max_length=18, repr=False)
    age: int | None = Field(default=None, ge=0, le=120)
    birth_date: date | None = None
    mobile_phone: str | None = Field(default=None, max_length=24)
    recovery_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=24)
    address_line: str | None = Field(default=None, max_length=180)
    address_number: str | None = Field(default=None, max_length=25)
    address_complement: str | None = Field(default=None, max_length=120)
    neighborhood: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    cep: str | None = Field(default=None, max_length=10)


def _account_identity_data(user_id: str) -> dict:
    db = get_supabase()
    user_result = db.table("users").select("id,email").eq("id", user_id).maybe_single().execute()
    if not user_result or not user_result.data:
        raise HTTPException(404, "Conta não encontrada.")
    result = (db.table("account_billing_identity").select("*")
              .eq("user_id", user_id).maybe_single().execute())
    # postgrest-py pode devolver None (em vez de APIResponse(data=None))
    # para maybe_single() sem linha. Contas antigas ainda não possuem
    # account_billing_identity: devem receber o formulário vazio, não HTTP 500.
    row = (result.data if result is not None else None) or {}
    public = {key: row.get(key) for key in (
        "full_name", "age", "birth_date", "mobile_phone", "recovery_email", "contact_phone",
        "address_line", "address_number", "address_complement", "neighborhood",
        "city", "state", "cep",
    )}
    public["cpf_registered"] = bool(row.get("cpf_ciphertext"))
    public["email"] = user_result.data.get("email")
    public["purchase_readiness"] = purchase_readiness(user_result.data, row)
    return public


@router.get("/me/identity")
def get_own_identity(user_id: str = Depends(get_current_user_id)):
    return _account_identity_data(user_id)


@router.get("/me/purchase-readiness")
def get_purchase_readiness(user_id: str = Depends(get_current_user_id)):
    """Contrato obrigatório para o futuro checkout; não cria pedido/pagamento."""
    return _account_identity_data(user_id)["purchase_readiness"]


@router.put("/me/identity")
def update_own_identity(body: AccountIdentityUpdate, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    updates = body.model_dump(exclude_unset=True)
    cpf = updates.pop("cpf", None)
    if "full_name" in updates:
        if not updates["full_name"]:
            raise HTTPException(422, "Nome e sobrenome são obrigatórios.")
        updates["full_name"] = normalize_full_name(updates["full_name"])
    if updates.get("birth_date") is not None:
        if updates["birth_date"] > date.today():
            raise HTTPException(422, "A data de nascimento não pode ser futura.")
        updates["birth_date"] = updates["birth_date"].isoformat()
    if cpf is not None and cpf.strip():
        updates.update(cpf_record(cpf))
    if "mobile_phone" in updates:
        updates["mobile_phone"] = normalize_phone(updates["mobile_phone"], mobile=True)
    if "contact_phone" in updates:
        updates["contact_phone"] = normalize_phone(updates["contact_phone"])
    if "cep" in updates:
        updates["cep"] = normalize_cep(updates["cep"])
    if "recovery_email" in updates and updates["recovery_email"]:
        from .supabase_auth import _normalized_email
        updates["recovery_email"] = _normalized_email(updates["recovery_email"])
    for field in ("address_line", "address_number", "address_complement", "neighborhood", "city", "state"):
        if field in updates and updates[field] is not None:
            updates[field] = updates[field].strip() or None
    if updates.get("state") and not re.fullmatch(r"[A-Za-z]{2}", updates["state"]):
        raise HTTPException(422, "UF deve ter duas letras.")
    if updates.get("state"):
        updates["state"] = updates["state"].upper()
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            # Um UPSERT com colunas ausentes pode enviar NULL no merge do
            # PostgREST e apagar o CPF cifrado. Em edições parciais, UPDATE
            # preserva todas as colunas não enviadas.
            current = (db.table("account_billing_identity").select("user_id")
                       .eq("user_id", user_id).maybe_single().execute())
            if current is not None and current.data:
                (db.table("account_billing_identity").update(updates)
                 .eq("user_id", user_id).execute())
            else:
                db.table("account_billing_identity").insert({"user_id": user_id, **updates}).execute()
        except Exception:
            # Não mostrar índice/fingerprint ou os dados enviados nas falhas.
            raise HTTPException(409, "Não foi possível salvar os dados. Verifique o CPF ou tente novamente.") from None
    return _account_identity_data(user_id)
logger = logging.getLogger("uvicorn.error")


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
    source_profile_id: str | None = None


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


def _delete_user_row(user_id: str | int) -> dict:
    """Orquestra Storage/Auth/DB; nunca cai no DELETE parcial legado."""
    if not account_erasure_enabled():
        raise HTTPException(
            status_code=503,
            detail="Exclusão integral da conta em preparação. Nenhum dado foi removido.",
        )
    try:
        return erase_account(str(user_id))
    except Exception as exc:
        # A fase inicial pode já ter bloqueado a conta. Operação é retomável
        # por admin; não revelar dados internos, tokens ou nomes de arquivos.
        logger.warning("Apagamento integral interrompido (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Exclusão não concluída. A conta ficou protegida; solicite a retomada ao suporte.",
        ) from None


def _verify_self_delete_password(account: dict, password: str) -> None:
    """Conta Auth exige prova de senha no próprio Auth, não hash legado."""
    linked_id = account.get("supabase_auth_user_id")
    if linked_id:
        if not (settings.supabase_url and settings.supabase_auth_publishable_key and account.get("email")):
            raise HTTPException(status_code=503, detail="Verificação de identidade indisponível.")
        try:
            # Cliente efêmero com chave publicável: NÃO autenticar na sessão
            # global de service_role do backend.
            verifier = create_client(settings.supabase_url, settings.supabase_auth_publishable_key)
            result = verifier.auth.sign_in_with_password({
                "email": account["email"], "password": password,
            })
            verified_id = getattr(getattr(result, "user", None), "id", None)
        except Exception as exc:
            code = getattr(exc, "status_code", getattr(exc, "status", None))
            if str(code) in {"400", "401", "403", "422"}:
                raise HTTPException(status_code=403, detail="Senha atual incorreta") from None
            logger.warning("Confirmação Auth indisponível (%s)", type(exc).__name__)
            raise HTTPException(status_code=503, detail="Verificação de identidade indisponível.") from None
        if str(verified_id) != str(linked_id):
            raise HTTPException(status_code=403, detail="Senha atual incorreta")
    else:
        try:
            valid = pwd_context.verify(password, account.get("password") or "")
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise HTTPException(status_code=403, detail="Senha atual incorreta")


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

    data = {
        "products": products,
        "product_lists": product_lists,
        "posts": posts,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    if profile_id:
        data["source_profile_id"] = profile_id
    return data


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
        supabase.table("users").select("username, access, password, email, supabase_auth_user_id").eq("id", user_id)
        .single().execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if current.data.get("username", "").lower() == "rafastudio":
        raise HTTPException(status_code=403, detail="Esta conta não pode ser removida")

    # Checar proteção e gate antes de qualquer side effect. Em caso de Auth
    # vinculado, a senha atual é validada no Auth, não em hash desatualizado.
    await run_in_threadpool(_verify_self_delete_password, current.data, body.current_password)
    if not account_erasure_enabled():
        raise HTTPException(status_code=503, detail="Exclusão integral da conta em preparação. Nenhum dado foi removido.")
    await run_in_threadpool(_delete_user_row, user_id)

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
    (comparação com `hmac.compare_digest`, constante no tempo). Quando há
    listas ou posts, `source_profile_id` é protegido pelo mesmo HMAC e precisa
    corresponder ao perfil ativo; catálogo compartilhado pode ser restaurado
    sem esse marcador.

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
    if "source_profile_id" in body.model_fields_set:
        payload["source_profile_id"] = body.source_profile_id
    if not hmac.compare_digest(_checksum(payload), body.checksum):
        raise HTTPException(status_code=400, detail="Arquivo de backup corrompido ou inválido.")
    if (body.product_lists or body.posts) and not profile_id:
        raise HTTPException(status_code=400, detail="Perfil ativo obrigatório para restaurar listas ou posts.")
    if (body.product_lists or body.posts) and body.source_profile_id != profile_id:
        raise HTTPException(status_code=400, detail="Backup contém dados isolados de outro perfil.")

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


async def delete_user(user_id: str, _admin_id: str = Depends(_require_admin)):
    current = (
        supabase.table("users").select("username, access").eq("id", user_id)
        .single().execute()
    )
    if current.data and current.data.get("username", "").lower() == "rafastudio":
        raise HTTPException(status_code=403, detail="Esta conta não pode ser removida")

    await run_in_threadpool(_delete_user_row, user_id)

    return {"msg": "Usuário removido"}


async def resume_erasure(user_id: str, _admin_id: str = Depends(_require_admin)):
    """Retomada manual por admin; não adiciona cron e não repete publicação."""
    await run_in_threadpool(_delete_user_row, user_id)
    return {"msg": "Exclusão integral concluída"}
