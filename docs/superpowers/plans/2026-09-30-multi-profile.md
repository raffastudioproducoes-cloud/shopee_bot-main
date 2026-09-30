# Sistema de Múltiplos Perfis + Git Flow com Staging — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que uma conta (login) do Shopee Auto Vendas gerencie até 3 perfis
("lojas") isolados, e migrar o fluxo de desenvolvimento pra Git Flow com staging e SemVer.

**Architecture:** Nova tabela `profiles` (sub-tenant dentro de `user_id`), claim
`profile_id` no JWT existente, coluna `profile_id` nullable aditiva em `products` e
`product_lists` (escopo desta rodada — ver nota de escopo abaixo), página `UsersPage.tsx`
reaproveitada e renomeada pra `ProfilesPage.tsx` com seção admin preservada. Infra: rename
`master`→`main`, branch `staging` com Web Service Render free + branch de banco Supabase.

**Tech Stack:** FastAPI + Pydantic + supabase-py (backend), React 19 + TanStack
Router/Query + Vite 6 + Tailwind 4 (frontend), PostgreSQL/Supabase.

**Spec:** `docs/superpowers/specs/2026-09-30-multi-profile-design.md`

## Nota de escopo (decisão do orquestrador, não do spec)

O spec (seção 2.3) pede `profile_id` em **todas** as tabelas do projeto (14+ tabelas:
credenciais de cada rede, posts, mídias, activities, schedulers, audit_events,
request_logs). Fazer isso de uma vez num único plano seria irreal de revisar e testar.
Este plano cobre o **núcleo funcional demonstrável**: `products` e `product_lists`
(Task 6) — o suficiente para perfis terem catálogo e listas isolados de ponta a ponta.
As demais tabelas continuam filtrando só por `user_id` (comportamento atual, não quebra
nada) até uma rodada seguinte de migração explicitamente planejada. Isso é aditivo e
seguro: nenhuma tabela ganha `NOT NULL` em `profile_id`, então código antigo continua
funcionando.

## Global Constraints

- `users.id` é `UUID`, não inteiro — qualquer novo código que manipule `user_id`/`profile_id`
  usa `str`/`UUID`, nunca `int` (o `-> int` em `get_current_user_id` hoje é um tipo
  incorreto legado — não copiar esse erro em código novo).
- JWT payload hoje: `{"sub": username, "id": user_id, "exp": ...}`, assinado com
  `settings.api_secret_key`, algoritmo `HS256` fixo (`api/routers/auth.py`).
- `users` **não tem coluna `email`** — `profiles.email` nasce `NULL` para o perfil
  principal migrado automaticamente (usuário completa depois).
- Toda rota nova sem barra final (`docs/RULES.md`).
- `.strip()` defensivo em toda leitura de credencial/valor de formulário sensível.
- Nunca reexibir segredo salvo.
- RLS: toda tabela nova recebe `enable row level security` + `create policy "block_all_api" ... using (false) with check (false)` (padrão de TODAS as tabelas existentes — service_role do backend ignora RLS, isso só bloqueia acesso via API REST pública do Supabase).
- Toda migração aplicada em produção via MCP direto (fora do boot do app) **precisa** ser
  registrada na mesma hora em `public.migrations` (`insert into public.migrations (name, aplied_at) values (...)`) — incidente real de 2026-09-30, documentado em `docs/RULES.md` item 9. Prefira deixar o próprio app aplicar no boot quando possível.
- Próximo número de migração livre: `035`.
- Testes de backend: `python -m pytest tests/api --confcutdir=tests/api -q` (nunca `pytest` puro).
- Frontend: `npx tsc --noEmit` e `npm run build` limpos antes de qualquer commit.
- Commits em português, tipo `feat:`/`fix:`/`docs:`, **sem linha de atribuição/co-author**.

## Review Focus

- Usuário comum tenta criar um 4º perfil (limite de 3 já atingido) — deve receber 400/403 claro, nunca criar silenciosamente um 4º.
- Usuário tenta deletar o próprio perfil `principal` — deve ser bloqueado (só secundários são deletáveis).
- Token JWT antigo (emitido antes desta feature, sem claim `profile_id`) chega num endpoint que exige perfil ativo — deve cair num fallback seguro (perfil principal do usuário), não quebrar com 500/KeyError.
- Usuário comum (não admin) chama a API de criar perfil pra OUTRO `user_id` (tentando manipular o próprio perfil de outra conta) — deve ser bloqueado por IDOR, igual ao padrão já usado em `lists.py::_sync_list_products`.
- Upload de avatar com arquivo que não é imagem de verdade (extensão de imagem mas conteúdo binário arbitrário) — deve ser rejeitado pela validação de magic-byte (`fleep`), não só pela extensão.

---

### Task 1: Git Flow — renomear branch e atualizar CI/CD

**Files:**
- Modify: `.github/workflows/ci.yml:5,7`
- Modify: `.github/workflows/cd.yml:5`
- Owner: **orquestrador direto** (operação de conta GitHub, `gh` CLI — não delega a subagente de código).

**Interfaces:**
- Produces: branch padrão do repositório passa a ser `main`; `master` deixa de existir.

- [ ] **Step 1: Renomear a branch no GitHub (também renomeia o remote local no próximo fetch)**

```bash
gh api -X POST repos/raffastudioproducoes-cloud/shopee_bot-main/branches/master/rename -f new_name=main
```

Isso já reaponta a branch padrão do repositório e redireciona PRs/comparações antigas
automaticamente (comportamento nativo do GitHub).

- [ ] **Step 2: Atualizar o remote local**

```bash
git fetch origin
git branch -m master main
git branch -u origin/main main
git remote set-head origin -a
```

- [ ] **Step 3: Editar `ci.yml` e `cd.yml`**

Em `.github/workflows/ci.yml`, trocar:
```yaml
on:
  push:
    branches: [master]
  pull_request:
    branches: [master]
```
por:
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

Em `.github/workflows/cd.yml`, trocar:
```yaml
on:
  push:
    branches: [master]
```
por:
```yaml
on:
  push:
    branches: [main]
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/cd.yml
git commit -m "ci: atualiza referencias de branch master para main"
```

- [ ] **Step 5: Proteger `main` (exige PR, bloqueia force-push e commit direto)**

```bash
gh api -X PUT repos/raffastudioproducoes-cloud/shopee_bot-main/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks=null \
  -F enforce_admins=true \
  -f required_pull_request_reviews[required_approving_review_count]=0 \
  -f restrictions=null \
  -F allow_force_pushes=false \
  -F allow_deletions=false
```

`required_approving_review_count=0` porque é projeto solo (Rafa é o único revisor
possível) — a regra real que importa aqui é **exigir PR** (bloqueia push direto) e
**bloquear force-push/deleção**, não exigir aprovação de terceiro que não existe.

- [ ] **Step 6: Verificar**

```bash
gh api repos/raffastudioproducoes-cloud/shopee_bot-main/branches/main/protection
```
Esperado: JSON confirmando `"allow_force_pushes": false` e a regra de PR ativa.

---

### Task 2: Ambiente de staging (Render + Supabase branch)

**Files:** nenhum arquivo de código — infraestrutura via MCP.
- Owner: **orquestrador direto** (MCP Render + MCP Supabase — provisionamento de conta/infra, nunca delegado a subagente de código).

**Interfaces:**
- Produces: branch `staging` no git; Web Service Render novo (`shopee-bot-staging`, free) fazendo deploy automático dessa branch; branch de banco Supabase `staging` isolada da produção.

- [ ] **Step 1: Criar a branch `staging` a partir de `main`**

```bash
git checkout main
git pull origin main
git checkout -b staging
git push -u origin staging
```

- [ ] **Step 2: Criar a branch de banco no Supabase (isola schema de teste da produção)**

Via MCP Supabase (`mcp__e1ff03fd-...__create_branch`), `project_id` do projeto `autovendas`
(`wcentenooirmwwlwlljp`), nome `staging`. Se o plano free não permitir branch de banco
persistente, documentar isso no PR e usar como fallback um schema `staging.*` dentro do
mesmo projeto (decisão tomada em runtime, não bloqueia o restante do plano).

- [ ] **Step 3: Criar o Web Service de staging no Render**

Via MCP Render (`mcp__9e9fe58d-...__create_web_service`), mesmo repositório GitHub,
branch `staging`, plano `free`, mesmo `Dockerfile`/`gunicorn.conf.py` do serviço de
produção. Variáveis de ambiente: copiar as mesmas do serviço de produção, exceto
`SUPABASE_URL`/`SUPABASE_KEY` (apontar pra branch de banco de staging do Step 2) e
`RENDER_DEPLOY_HOOK_URL` do `cd.yml` de staging (novo hook, não reaproveitar o de
produção).

- [ ] **Step 4: Adicionar workflow de deploy pra staging**

Criar `.github/workflows/cd-staging.yml`:
```yaml
name: CD Staging — Deploy no Render

on:
  push:
    branches: [staging]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Trigger Render Deploy (staging)
        env:
          RENDER_STAGING_DEPLOY_HOOK_URL: ${{ secrets.RENDER_STAGING_DEPLOY_HOOK_URL }}
        run: |
          if [ -z "$RENDER_STAGING_DEPLOY_HOOK_URL" ]; then
            echo "::warning::RENDER_STAGING_DEPLOY_HOOK_URL nao configurado. Ignoring deploy."
            exit 0
          fi
          curl -s -X POST "$RENDER_STAGING_DEPLOY_HOOK_URL"
```

- [ ] **Step 5: Commit e push**

```bash
git add .github/workflows/cd-staging.yml
git commit -m "ci: adiciona deploy automatico de staging"
git push origin staging
```

- [ ] **Step 6: Verificar**

Chamar `mcp__9e9fe58d-...__get_deploy` até `status: "live"` no novo serviço, depois
testar `curl` na URL de staging (`/api/health`) — deve responder 200, isolado da produção.

---

### Task 3: Migração 035 — tabela `profiles` + backfill do perfil principal

**Files:**
- Create: `database/migrations/035_create_profiles_table.sql`
- Test: `tests/api/test_profiles_migration.py`

**Interfaces:**
- Produces: tabela `public.profiles` (colunas: `id uuid`, `user_id uuid`, `kind text`,
  `plan_tier text`, `nome text`, `email text`, `telefone text`, `endereco text`,
  `avatar_url text`, `created_at`, `updated_at`), com 1 linha `kind='principal'` para
  cada `user_id` já existente em `users`.

- [ ] **Step 1: Escrever a migração**

```sql
-- database/migrations/035_create_profiles_table.sql
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  kind text not null check (kind in ('principal', 'secundario')),
  plan_tier text not null default 'free' check (plan_tier in ('free', 'plus', 'premium')),
  nome text not null,
  email text,
  telefone text,
  endereco text,
  avatar_url text,
  created_at timestamp not null default current_timestamp,
  updated_at timestamp not null default current_timestamp
);

create index if not exists idx_profiles_user_id on public.profiles (user_id);

alter table public.profiles enable row level security;
create policy "block_all_api" on public.profiles for all using (false) with check (false);

-- Backfill: cada usuario existente ganha 1 perfil principal automaticamente.
insert into public.profiles (user_id, kind, nome)
select id, 'principal', username
from public.users
where not exists (
  select 1 from public.profiles p where p.user_id = users.id and p.kind = 'principal'
);
```

- [ ] **Step 2: Escrever teste de regressão (confirma que a migração é idempotente e cria o backfill certo)**

```python
# tests/api/test_profiles_migration.py
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "database" / "migrations" / "035_create_profiles_table.sql"


def test_migration_file_exists_and_has_block_all_api_policy():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "create table if not exists public.profiles" in sql
    assert 'create policy "block_all_api" on public.profiles' in sql
    assert "on delete cascade" in sql


def test_migration_backfill_is_idempotent():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "where not exists" in sql
```

- [ ] **Step 3: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/api/test_profiles_migration.py -v --confcutdir=tests/api`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add database/migrations/035_create_profiles_table.sql tests/api/test_profiles_migration.py
git commit -m "feat: migracao 035 - tabela profiles com backfill do perfil principal"
```

---

### Task 4: Migração 036 — `profile_id` aditivo em `products` e `product_lists`

**Files:**
- Create: `database/migrations/036_add_profile_id_to_products_and_lists.sql`
- Test: `tests/api/test_profile_id_migration.py`

**Interfaces:**
- Consumes: tabela `profiles` (Task 3).
- Produces: coluna `profile_id uuid` (nullable) em `products` e `product_lists`,
  populada com o `id` do perfil `principal` de cada `user_id` dono da linha.

- [ ] **Step 1: Escrever a migração**

```sql
-- database/migrations/036_add_profile_id_to_products_and_lists.sql
alter table public.products add column if not exists profile_id uuid references profiles(id) on delete set null;
alter table public.product_lists add column if not exists profile_id uuid references profiles(id) on delete set null;

create index if not exists idx_products_profile_id on public.products (profile_id);
create index if not exists idx_product_lists_profile_id on public.product_lists (profile_id);

update public.products p
set profile_id = pr.id
from public.profiles pr
where pr.user_id = p.user_id and pr.kind = 'principal' and p.profile_id is null;

update public.product_lists pl
set profile_id = pr.id
from public.profiles pr
where pr.user_id = pl.user_id and pr.kind = 'principal' and pl.profile_id is null;
```

`on delete set null` (não `cascade`) — deletar um perfil secundário não deve destruir os
produtos associados a ele silenciosamente (mesma lógica de preservação de dado já usada
na FK de `audit_events.user_id`, ver `docs/RULES.md` histórico do incidente de 2026-09-30).

- [ ] **Step 2: Escrever teste de regressão**

```python
# tests/api/test_profile_id_migration.py
from pathlib import Path

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "database" / "migrations" / "036_add_profile_id_to_products_and_lists.sql"


def test_migration_adds_nullable_profile_id_with_set_null():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "add column if not exists profile_id uuid" in sql
    assert "on delete set null" in sql
    assert "on delete cascade" not in sql


def test_migration_backfills_from_principal_profile():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "kind = 'principal'" in sql
```

- [ ] **Step 3: Rodar e confirmar**

Run: `python -m pytest tests/api/test_profile_id_migration.py -v --confcutdir=tests/api`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add database/migrations/036_add_profile_id_to_products_and_lists.sql tests/api/test_profile_id_migration.py
git commit -m "feat: migracao 036 - profile_id aditivo em products e product_lists"
```

---

### Task 5: Backend — módulo `profiles`, router, claim `profile_id` no JWT

**Files:**
- Create: `api/profiles.py`
- Create: `api/routers/profiles.py`
- Modify: `api/routers/auth.py` (login emite claim `profile_id`; nova dependency `get_current_profile_id`)
- Modify: `api/main.py` (registra `profiles_router`)
- Modify: `api/routers/__init__.py` (exporta `profiles_router`)
- Test: `tests/api/test_profiles.py`

**Interfaces:**
- Consumes: `get_current_user_id` (`api/routers/auth.py`), `supabase` proxy (`api/database.py`), `_create_token`/`_decode_token` (`api/routers/auth.py`).
- Produces: `get_current_profile_id(request: Request) -> str` (dependency reusável por outros routers na Task 6); `PROFILE_LIMIT = 3` (constante reusável).

- [ ] **Step 1: Escrever o teste do limite de 3 perfis (falha primeiro — TDD)**

```python
# tests/api/test_profiles.py
from unittest.mock import MagicMock, patch


def _mock_supabase_with_profiles(count: int, principal_id: str = "p-1"):
    client = MagicMock()
    existing = [{"id": f"p-{i}", "kind": "secundario"} for i in range(count)]
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = existing
    return client


def test_create_profile_blocked_when_limit_of_three_reached(client, auth_headers):
    with patch("api.routers.profiles.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1", "kind": "principal"},
            {"id": "p-2", "kind": "secundario"},
            {"id": "p-3", "kind": "secundario"},
        ]
        response = client.post(
            "/profiles",
            json={"nome": "Loja 4", "email": "loja4@example.com"},
            cookies=auth_headers,
        )
    assert response.status_code == 400
    assert "limite" in response.json()["detail"].lower()


def test_delete_principal_profile_is_blocked(client, auth_headers):
    with patch("api.routers.profiles.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "p-1", "user_id": "u-1", "kind": "principal",
        }
        response = client.delete("/profiles/p-1", cookies=auth_headers)
    assert response.status_code == 400
```

(Fixtures `client`/`auth_headers` seguem o mesmo padrão já usado em `tests/api/test_users.py` — confirme o nome exato dessas fixtures em `tests/api/conftest.py` antes de rodar; se o nome for diferente, ajuste a assinatura do teste pra bater, sem mudar o comportamento testado.)

- [ ] **Step 2: Rodar e confirmar que falha (função ainda não existe)**

Run: `python -m pytest tests/api/test_profiles.py -v --confcutdir=tests/api`
Expected: FAIL com `ModuleNotFoundError: No module named 'api.routers.profiles'`.

- [ ] **Step 3: Implementar `api/profiles.py` (regra de negócio pura)**

```python
# api/profiles.py
PROFILE_LIMIT = 3
VALID_KINDS = ("principal", "secundario")
VALID_PLAN_TIERS = ("free", "plus", "premium")


def can_create_profile(existing_count: int) -> bool:
    return existing_count < PROFILE_LIMIT


def is_principal(profile: dict) -> bool:
    return profile.get("kind") == "principal"
```

- [ ] **Step 4: Implementar `api/routers/profiles.py`**

```python
# api/routers/profiles.py
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from ..database import supabase
from ..profiles import PROFILE_LIMIT, can_create_profile, is_principal
from .auth import _create_token, _decode_token, get_current_user_id

router = APIRouter(prefix="/profiles", tags=["profiles"])


class ProfileCreate(BaseModel):
    nome: str
    email: str
    telefone: str | None = None
    endereco: str | None = None


class ProfileUpdate(BaseModel):
    nome: str
    email: str
    telefone: str | None = None
    endereco: str | None = None


def get_current_profile_id(request: Request) -> str | None:
    """Claim opcional -- token emitido antes desta feature nao tem profile_id."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    return payload.get("profile_id")


@router.get("")
async def list_profiles(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
    return result.data


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreate, user_id: str = Depends(get_current_user_id)):
    existing = (
        supabase.table("profiles").select("id").eq("user_id", user_id).execute()
    )
    if not can_create_profile(len(existing.data or [])):
        raise HTTPException(
            status_code=400,
            detail=f"Limite de {PROFILE_LIMIT} perfis por conta atingido.",
        )
    result = (
        supabase.table("profiles")
        .insert({
            "user_id": user_id,
            "kind": "secundario",
            "nome": body.nome.strip(),
            "email": body.email.strip(),
            "telefone": body.telefone.strip() if body.telefone else None,
            "endereco": body.endereco.strip() if body.endereco else None,
        })
        .execute()
    )
    return result.data[0]


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str, body: ProfileUpdate, user_id: str = Depends(get_current_user_id)
):
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    result = (
        supabase.table("profiles")
        .update({
            "nome": body.nome.strip(),
            "email": body.email.strip(),
            "telefone": body.telefone.strip() if body.telefone else None,
            "endereco": body.endereco.strip() if body.endereco else None,
        })
        .eq("id", profile_id)
        .execute()
    )
    return result.data[0]


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str, user_id: str = Depends(get_current_user_id)):
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")
    if is_principal(existing.data):
        raise HTTPException(status_code=400, detail="O perfil principal não pode ser excluído")
    supabase.table("profiles").delete().eq("id", profile_id).execute()
    return {"status": "deleted"}


@router.post("/{profile_id}/activate")
async def activate_profile(
    profile_id: str,
    response: Response,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    token = request.cookies.get("access_token")
    payload = _decode_token(token) if token else None
    username = payload.get("sub") if payload else None
    new_token = _create_token({"sub": username, "id": user_id, "profile_id": profile_id})

    # Copiar EXATAMENTE os mesmos parametros de response.set_cookie(...) usados no
    # endpoint de login em api/routers/auth.py (httponly/secure/samesite/max_age) --
    # nao reinvente esses flags, leia o login atual e reproduza.
    response.set_cookie(key="access_token", value=new_token, httponly=True)
    return {"status": "activated", "profile_id": profile_id}
```

- [ ] **Step 5: Registrar o router**

Em `api/routers/__init__.py`, adicionar ao lado dos outros:
```python
from .profiles import router as profiles_router
```

Em `api/main.py`, ao lado dos demais `app.include_router(...)`:
```python
app.include_router(profiles_router)
```

- [ ] **Step 6: Adicionar claim `profile_id` no login**

Em `api/routers/auth.py`, na função `login`, onde hoje chama
`_create_token({"sub": user["username"], "id": user["id"]})`, trocar para buscar o
perfil principal do usuário e incluir o claim:

```python
principal = (
    supabase.table("profiles")
    .select("id")
    .eq("user_id", user["id"])
    .eq("kind", "principal")
    .maybe_single()
    .execute()
)
profile_id = principal.data["id"] if principal.data else None
token = _create_token({"sub": user["username"], "id": user["id"], "profile_id": profile_id})
```

(Import `supabase` já deve existir em `auth.py` ou precisa ser adicionado — confirme
antes de editar.)

- [ ] **Step 7: Rodar os testes e confirmar que passam**

Run: `python -m pytest tests/api/test_profiles.py -v --confcutdir=tests/api`
Expected: PASS.

- [ ] **Step 8: Rodar a suite completa**

Run: `python -m pytest tests/api --confcutdir=tests/api -q`
Expected: todos os testes anteriores continuam verdes + os novos.

- [ ] **Step 9: Commit**

```bash
git add api/profiles.py api/routers/profiles.py api/routers/auth.py api/main.py api/routers/__init__.py tests/api/test_profiles.py
git commit -m "feat: CRUD de perfis, limite de 3, claim profile_id no JWT"
```

---

### Task 6: Backend — escopar `products` e `lists` por perfil ativo

**Files:**
- Modify: `api/routers/products.py` (endpoints `list_products`, `create_product`, helper de ownership)
- Modify: `api/routers/lists.py` (endpoints `list_product_lists`, `create_product_list`, `_get_list`)
- Test: `tests/api/test_products.py` (estender), `tests/api/test_lists.py` (estender)

**Interfaces:**
- Consumes: `get_current_profile_id` (Task 5, `api/routers/profiles.py`).
- Produces: produtos/listas passam a ser filtrados também por `profile_id` quando o
  token carrega essa claim; tokens antigos (sem `profile_id`) continuam funcionando
  filtrando só por `user_id` (fallback, nunca quebra sessão existente).

- [ ] **Step 1: Escrever teste — perfil A não vê produto do perfil B (mesma conta)**

```python
# tests/api/test_products.py (adicionar)
from unittest.mock import patch


def test_list_products_filters_by_active_profile_when_token_has_profile_id(client, auth_headers_with_profile):
    with patch("api.routers.products.supabase") as mock_supabase:
        query = mock_supabase.table.return_value.select.return_value.eq.return_value
        query.eq.return_value.range.return_value.execute.return_value.data = []
        client.get("/products", cookies=auth_headers_with_profile)
        # confirma que .eq("profile_id", ...) foi chamado em cima de .eq("user_id", ...)
        query.eq.assert_called_with("profile_id", "profile-a")
```

(Se a fixture `auth_headers_with_profile` não existir ainda em `tests/api/conftest.py`,
crie-a: mesmo cookie de `auth_headers`, mas com um JWT que carrega `profile_id: "profile-a"`
no payload, gerado com a mesma `_create_token` de `auth.py`.)

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/api/test_products.py -k profile -v --confcutdir=tests/api`
Expected: FAIL (filtro por `profile_id` ainda não existe).

- [ ] **Step 3: Implementar em `products.py`**

Em `list_products` (`products.py:81-92` e corpo da função), adicionar dependency e filtro:
```python
from .profiles import get_current_profile_id

async def list_products(
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
    ...
):
    query = supabase.table("products").select("*").eq("user_id", user_id)
    if profile_id:
        query = query.eq("profile_id", profile_id)
    ...
```

Em `create_product`, adicionar `profile_id` no dict do insert quando presente:
```python
async def create_product(
    body: ProductCreate,
    user_id: str = Depends(get_current_user_id),
    profile_id: str | None = Depends(get_current_profile_id),
):
    data = {"user_id": user_id, "product_id": body.product_id, ...}
    if profile_id:
        data["profile_id"] = profile_id
    result = supabase.table("products").insert(data).execute()
```

- [ ] **Step 4: Repetir o mesmo padrão em `lists.py`** (`list_product_lists`, `create_product_list`, `_get_list`) — mesma dependency, mesmo `if profile_id: query = query.eq("profile_id", profile_id)`.

- [ ] **Step 5: Rodar os testes específicos e depois a suite completa**

Run: `python -m pytest tests/api/test_products.py tests/api/test_lists.py -v --confcutdir=tests/api`
Expected: PASS.

Run: `python -m pytest tests/api --confcutdir=tests/api -q`
Expected: todos verdes (nenhuma regressão em token sem `profile_id`).

- [ ] **Step 6: Commit**

```bash
git add api/routers/products.py api/routers/lists.py tests/api/test_products.py tests/api/test_lists.py
git commit -m "feat: escopa produtos e listas pelo perfil ativo (aditivo, compatível com token antigo)"
```

---

### Task 7: Backend — upload de avatar via Supabase Storage

**Files:**
- Modify: `api/routers/profiles.py` (novo endpoint `POST /profiles/{profile_id}/avatar`)
- Test: `tests/api/test_profiles.py` (estender)

**Interfaces:**
- Consumes: `fleep` (já usado em `api/routers/posts.py` para validação de magic-byte — mesmo padrão).
- Produces: `profiles.avatar_url` atualizado com a URL pública do arquivo no bucket `avatars`.

- [ ] **Step 1: Escrever o teste (upload recusado por conteúdo não ser imagem de verdade)**

```python
# tests/api/test_profiles.py (adicionar)
def test_avatar_upload_rejects_non_image_content(client, auth_headers):
    fake_file = ("avatar.png", b"isso nao e uma imagem de verdade", "image/png")
    with patch("api.routers.profiles.supabase") as mock_supabase:
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": "p-1", "user_id": "u-1",
        }
        response = client.post(
            "/profiles/p-1/avatar",
            files={"file": fake_file},
            cookies=auth_headers,
        )
    assert response.status_code == 400
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/api/test_profiles.py -k avatar -v --confcutdir=tests/api`
Expected: FAIL (endpoint não existe, 404).

- [ ] **Step 3: Implementar o endpoint**

```python
# api/routers/profiles.py (adicionar)
import fleep
from fastapi import File, UploadFile

ALLOWED_AVATAR_MIMES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_BUCKET = "avatars"


@router.post("/{profile_id}/avatar")
async def upload_avatar(
    profile_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    existing = (
        supabase.table("profiles")
        .select("*")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Perfil não encontrado")

    content = await file.read()
    info = fleep.get(content[:128])
    if not info.mime or info.mime[0] not in ALLOWED_AVATAR_MIMES:
        raise HTTPException(status_code=400, detail="Arquivo não é uma imagem válida.")

    path = f"{profile_id}/{file.filename}"
    supabase.storage.from_(AVATAR_BUCKET).upload(
        path, content, {"content-type": info.mime[0], "upsert": "true"}
    )
    public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(path)

    supabase.table("profiles").update({"avatar_url": public_url}).eq("id", profile_id).execute()
    return {"avatar_url": public_url}
```

- [ ] **Step 4: Criar o bucket no Supabase (owner: orquestrador, MCP direto, não faz parte do código)**

Via MCP Supabase `execute_sql` (ou painel), criar o bucket `avatars` público para leitura:
```sql
insert into storage.buckets (id, name, public) values ('avatars', 'avatars', true)
on conflict (id) do nothing;
```

- [ ] **Step 5: Rodar os testes**

Run: `python -m pytest tests/api/test_profiles.py -v --confcutdir=tests/api`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/routers/profiles.py tests/api/test_profiles.py
git commit -m "feat: upload de avatar de perfil via Supabase Storage com validacao de magic-byte"
```

---

### Task 8: Backend — troca de senha em `/settings`

**Files:**
- Create: `api/routers/settings.py`
- Modify: `api/main.py`, `api/routers/__init__.py`
- Test: `tests/api/test_settings.py`

**Interfaces:**
- Consumes: `get_current_user_id`, `pwd_context` (mesmo objeto bcrypt já usado em `api/routers/auth.py` para verificar senha).
- Produces: `PUT /settings/password`.

- [ ] **Step 1: Escrever o teste (senha atual errada não troca a senha)**

```python
# tests/api/test_settings.py
from unittest.mock import patch


def test_change_password_rejects_wrong_current_password(client, auth_headers):
    with patch("api.routers.settings.supabase") as mock_supabase, \
         patch("api.routers.settings.pwd_context") as mock_pwd:
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "u-1", "password": "hash-antigo",
        }
        mock_pwd.verify.return_value = False
        response = client.put(
            "/settings/password",
            json={"current_password": "errada", "new_password": "nova123"},
            cookies=auth_headers,
        )
    assert response.status_code == 403
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/api/test_settings.py -v --confcutdir=tests/api`
Expected: FAIL (módulo não existe).

- [ ] **Step 3: Implementar**

```python
# api/routers/settings.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..database import supabase
from .auth import get_current_user_id, pwd_context

router = APIRouter(prefix="/settings", tags=["settings"])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.put("/password")
async def change_password(body: PasswordChange, user_id: str = Depends(get_current_user_id)):
    result = (
        supabase.table("users").select("id, password").eq("id", user_id).single().execute()
    )
    if not result.data or not pwd_context.verify(body.current_password, result.data["password"]):
        raise HTTPException(status_code=403, detail="Senha atual incorreta")

    new_hash = pwd_context.hash(body.new_password)
    supabase.table("users").update({"password": new_hash}).eq("id", user_id).execute()
    return {"status": "updated"}
```

(Se `pwd_context` não for importável diretamente de `auth.py` — confirme se está
declarado no nível do módulo — importe do mesmo lugar que `api/routers/auth.py` já
importa/instancia, não crie uma segunda instância de `CryptContext`.)

- [ ] **Step 4: Registrar o router** (mesmo padrão da Task 5, Step 5, em `main.py`/`__init__.py`).

- [ ] **Step 5: Rodar os testes**

Run: `python -m pytest tests/api/test_settings.py -v --confcutdir=tests/api`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add api/routers/settings.py api/main.py api/routers/__init__.py tests/api/test_settings.py
git commit -m "feat: endpoint de troca de senha em /settings"
```

---

### Task 9: Frontend — `UsersPage.tsx` → `ProfilesPage.tsx` com cards de perfil

**Files:**
- Create: `frontend/src/pages/ProfilesPage.tsx` (conteúdo migrado de `UsersPage.tsx` + seção nova)
- Create: `frontend/src/api/profiles.ts`
- Modify: `frontend/src/router.tsx` (rota `/profiles` no lugar de `/users`, import renomeado)
- Modify: `frontend/src/pages/PanelPage.tsx` (label do menu lateral)
- Delete: `frontend/src/pages/UsersPage.tsx` (conteúdo migrado, arquivo antigo removido)

**Interfaces:**
- Consumes: `Badge`, `Button`, `IconButton`, `Panel`, `Modal` (`frontend/src/components/ui/`).
- Produces: componente `ProfilesPage` exportado, rota `/profiles`.

- [ ] **Step 1: Criar o client de API**

```typescript
// frontend/src/api/profiles.ts
import { api } from "../lib/api"

export interface Profile {
  id: string
  user_id: string
  kind: "principal" | "secundario"
  plan_tier: "free" | "plus" | "premium"
  nome: string
  email: string
  telefone: string | null
  endereco: string | null
  avatar_url: string | null
}

export const profilesApi = {
  list: () => api.get<Profile[]>("/profiles"),
  create: (data: { nome: string; email: string; telefone?: string; endereco?: string }) =>
    api.post<Profile>("/profiles", data),
  update: (id: string, data: { nome: string; email: string; telefone?: string; endereco?: string }) =>
    api.put<Profile>(`/profiles/${id}`, data),
  remove: (id: string) => api.delete(`/profiles/${id}`),
  activate: (id: string) => api.post(`/profiles/${id}/activate`, {}),
  uploadAvatar: (id: string, file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    return api.postForm<{ avatar_url: string }>(`/profiles/${id}/avatar`, formData)
  },
}
```

(Confirme a assinatura exata de `api.get`/`api.post`/`api.put`/`api.delete` em
`frontend/src/lib/api.ts` antes de escrever isso — use os mesmos genéricos/formato já
usados em `frontend/src/api/users.ts`. Se não existir `api.postForm` pra multipart,
adicione-o em `lib/api.ts` seguindo o mesmo padrão dos outros métodos, só trocando
`Content-Type`/body pra `FormData` sem serializar como JSON.)

- [ ] **Step 2: Copiar `UsersPage.tsx` para `ProfilesPage.tsx` e renomear o componente**

Copiar o arquivo inteiro, trocar `export function UsersPage()` por
`export function ProfilesPage()`. Manter TODO o conteúdo admin-only existente
(`UserModal`, lista de contas de login, gate `user?.access !== "ADMIN"` continua
controlando só a seção de contas de login, não a página inteira).

- [ ] **Step 3: Adicionar a seção de Perfis no topo do componente (visível pra TODOS, admin ou não)**

```tsx
// dentro de ProfilesPage(), antes da seção admin-only existente
const { data: profiles = [] } = useQuery({
  queryKey: ["profiles"],
  queryFn: () => profilesApi.list(),
})

const planTierLabel: Record<Profile["plan_tier"], string> = {
  free: "Free",
  plus: "Plus",
  premium: "Premium",
}
const kindLabel: Record<Profile["kind"], string> = {
  principal: "Principal",
  secundario: "Secundário",
}

return (
  <div>
    <h1>Perfis</h1>
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: 16,
      }}
    >
      {profiles.map((profile) => (
        <Panel key={profile.id} style={{ aspectRatio: "1 / 1", padding: 16 }}>
          <img
            src={profile.avatar_url ?? "/avatar-placeholder.png"}
            alt={profile.nome}
            style={{ width: "100%", aspectRatio: "1 / 1", objectFit: "cover", borderRadius: "var(--r-lg)" }}
          />
          <div style={{ marginTop: 8, fontWeight: 600 }}>{profile.nome}</div>
          <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{profile.email}</div>
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            <Badge tone={profile.plan_tier === "free" ? "neutral" : "mint"}>
              {planTierLabel[profile.plan_tier]}
            </Badge>
            <Badge tone={profile.kind === "principal" ? "mint" : "neutral"}>
              {kindLabel[profile.kind]}
            </Badge>
          </div>
        </Panel>
      ))}
    </div>
    {/* ... seção admin-only existente (contas de login) continua abaixo, sem mudança ... */}
  </div>
)
```

(Confirme o tone exato disponível em `Badge.tsx` antes de usar `"mint"`/`"neutral"` —
são os mesmos já usados em `UsersPage.tsx:146`, então devem existir; se `Badge.tsx`
tiver um terceiro tone mais adequado pra "Plus"/"Premium" se diferenciarem de
"Principal", use-o, mas não adicione um tone novo ao componente nesta tarefa.)

- [ ] **Step 4: Atualizar `router.tsx`**

Trocar:
```tsx
import { UsersPage } from "./pages/UsersPage"
...
const usersRoute = createRoute({ getParentRoute: () => panelRoute, path: "/users", component: UsersPage })
```
por:
```tsx
import { ProfilesPage } from "./pages/ProfilesPage"
...
const profilesRoute = createRoute({ getParentRoute: () => panelRoute, path: "/profiles", component: ProfilesPage })
```
E no `routeTree`, trocar `usersRoute` por `profilesRoute` na lista de children.

- [ ] **Step 5: Atualizar o label do menu lateral em `PanelPage.tsx`**

Achar a entrada de menu que hoje aponta pra `/users` (ícone + texto "Usuários") e trocar
o texto pra "Perfis", mantendo o mesmo ícone se fizer sentido ou troca por um ícone de
usuário/perfil já existente no wrapper `Icon.tsx`.

- [ ] **Step 6: Deletar o arquivo antigo**

```bash
rm frontend/src/pages/UsersPage.tsx
```

- [ ] **Step 7: Verificar**

Run: `npx tsc --noEmit`
Expected: sem erros (nenhuma referência a `UsersPage`/`usersRoute` sobrando).

Run: `npm run build`
Expected: build limpo.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/ProfilesPage.tsx frontend/src/api/profiles.ts frontend/src/router.tsx frontend/src/pages/PanelPage.tsx
git rm frontend/src/pages/UsersPage.tsx
git commit -m "feat: renomeia Usuarios para Perfis, adiciona grid de cards de perfil"
```

---

### Task 10: Frontend — página `/settings`

**Files:**
- Create: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/router.tsx` (nova rota `/settings`)
- Modify: `frontend/src/pages/PanelPage.tsx` (novo item de menu)

**Interfaces:**
- Consumes: `api.put` (`frontend/src/lib/api.ts`), `Button`, `TextInput`, `Panel`.

- [ ] **Step 1: Implementar a página**

```tsx
// frontend/src/pages/SettingsPage.tsx
import { useState } from "react"
import { Panel } from "../components/ui/Panel"
import { Button } from "../components/ui/Button"
import { TextInput } from "../components/ui/TextInput"
import { api } from "../lib/api"

export function SettingsPage() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle")

  async function handleSubmit() {
    setStatus("saving")
    try {
      await api.put("/settings/password", {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setStatus("done")
      setCurrentPassword("")
      setNewPassword("")
    } catch {
      setStatus("error")
    }
  }

  return (
    <div>
      <h1>Configurações</h1>
      <Panel style={{ maxWidth: 420, padding: 24 }}>
        <h2>Trocar senha</h2>
        <TextInput
          label="Senha atual"
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
        />
        <TextInput
          label="Nova senha"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
        <Button onClick={handleSubmit} loading={status === "saving"}>
          Salvar nova senha
        </Button>
        {status === "done" && <p>Senha atualizada.</p>}
        {status === "error" && <p>Senha atual incorreta.</p>}
      </Panel>
    </div>
  )
}
```

(Confirme a assinatura exata de `TextInput` — props `label`/`value`/`onChange`/`type` —
em `frontend/src/components/ui/TextInput.tsx` antes de usar; ajuste os nomes de prop se
forem diferentes, sem mudar o comportamento.)

- [ ] **Step 2: Atualizar `router.tsx`**

```tsx
import { SettingsPage } from "./pages/SettingsPage"
...
const settingsRoute = createRoute({ getParentRoute: () => panelRoute, path: "/settings", component: SettingsPage })
```
Adicionar `settingsRoute` na lista de `panelRoute.addChildren([...])`.

- [ ] **Step 3: Adicionar item de menu em `PanelPage.tsx`**

Mesmo padrão dos outros itens de menu (ícone + label "Configurações", rota `/settings`).

- [ ] **Step 4: Verificar**

Run: `npx tsc --noEmit` — sem erros.
Run: `npm run build` — limpo.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx frontend/src/router.tsx frontend/src/pages/PanelPage.tsx
git commit -m "feat: pagina de configuracoes com troca de senha"
```

---

### Task 11: Versionamento, documentação e merge final

**Files:**
- Create: `VERSION`
- Create/Modify: `CHANGELOG.md`
- Modify: `docs/TASK.md` (10.9 concluída)
- Modify: `docs/RULES.md` (registra o novo fluxo Git Flow/SemVer como regra permanente)

**Interfaces:** nenhuma (documentação/versionamento, sem código de aplicação).

- [ ] **Step 1: Criar o arquivo de versão**

```
2.0.0
```
(conteúdo literal de `VERSION`, sem quebra de linha extra)

- [ ] **Step 2: Criar/atualizar `CHANGELOG.md`**

```markdown
# Changelog

## [2.0.0] - 2026-09-30

### Added
- Sistema de múltiplos perfis por conta (até 3: 1 principal + 2 secundários), com
  isolamento de dados em produtos e listas.
- Upload de avatar de perfil via Supabase Storage.
- Página de Configurações (`/settings`) com troca de senha.
- Ambiente de staging (Render + branch de banco Supabase) e fluxo Git Flow
  (`main`/`staging`/`feature/*`) com proteção de branch e versionamento semântico.

### Changed
- Página "Usuários" renomeada para "Perfis" — contas de login de outros usuários
  (admin-only) continuam gerenciáveis na mesma página, agora como seção secundária.
- Branch padrão do repositório renomeada de `master` para `main`.
```

- [ ] **Step 3: Atualizar `docs/TASK.md` item 10.9**

Trocar `- [ ] **10.9 — Multi-perfil por conta.** ... Não iniciada/Bloqueada.` por
`- [x] **10.9 — Multi-perfil por conta.** Concluída. Limite de 3 perfis (1 principal +
2 secundários), tabela `profiles` (migração 035), `profile_id` aditivo em produtos/listas
(migração 036), avatar via Supabase Storage. (origem: benchmarking MiauDelier Manager,
2026-09-29; concluída: <data real da implementação>)`.

- [ ] **Step 4: Adicionar regra em `docs/RULES.md`**

Novo item registrando o fluxo Git Flow (branch `main` protegida, `staging`,
`feature/*`, SemVer só sobe no merge pra `main`) como prática permanente do projeto a
partir de 2026-09-30, substituindo a prática histórica de push direto documentada no
item 1.

- [ ] **Step 5: Commit na branch de feature**

```bash
git add VERSION CHANGELOG.md docs/TASK.md docs/RULES.md
git commit -m "docs: versao 2.0.0, changelog, atualiza TASK e RULES com o novo fluxo Git Flow"
```

- [ ] **Step 6: Abrir o PR pra `main` (não faz merge sozinho — Rafa aprova)**

```bash
git push -u origin feature/multi-profile
gh pr create --base main --head feature/multi-profile \
  --title "feat: sistema de multiplos perfis (v2.0.0)" \
  --body "Implementa o spec docs/superpowers/specs/2026-09-30-multi-profile-design.md. Ver CHANGELOG.md."
```

- [ ] **Step 7: Aguardar CI verde no PR e pedir revisão do Rafa antes do merge**

Não fazer merge automaticamente — esta é a primeira vez que o fluxo de PR obrigatório
é usado neste projeto; o merge final é uma decisão humana.
