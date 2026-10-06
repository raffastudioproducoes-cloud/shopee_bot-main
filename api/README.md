# API Python — ShopeeAutoVendas

Nova camada de API em FastAPI (async) que roda em background no mesmo container do Flask, acessível via proxy transparente `/api/*` do Flask.

## Arquitetura

- **`api/main.py`** — aplicação FastAPI
- **`api/routers/`** — endpoints organizados por domínio (auth, posts, products, credentials, users)
- **`api/internal_client.py`** — cliente HTTP para chamar bridge interno do Flask (`/internal/*`)
- **`api/database.py`** — acesso ao Supabase via cliente Python async
- **`api/crypto.py`** — criptografia Fernet (compatível com o `utils/crypto.py` do Flask)
- **`tests/api/`** — testes pytest (cobertura 80%+)

## Multi-perfil (perfil ativo)

O cookie `access_token` carrega o claim `profile_id` (perfil ativo, validado contra `profiles` por
`get_current_profile_id`). Com perfil ativo, leituras filtram e escritas gravam `profile_id`; sem perfil
(token antigo) o comportamento é o anterior, só por `user_id`. GET/PUT/DELETE por ID também filtram por
perfil (sem IDOR entre perfis da mesma conta). Helper: `api/profiles.py::scope_owner`.

| Tabela / rota | Escopo por `profile_id` |
|---|---|
| `products`, `product_lists` (`/products`, `/lists`) | leitura, escrita, por ID |
| `posts`, `medias` (`/posts`) | leitura, escrita, por ID; `profile_id` repassado ao bridge do scheduler |
| `*_credentials` e `credential_checks` (`/credentials`) | cada perfil tem as próprias credenciais e a própria luz de "Testar conexão" |
| `/products/catalog-search` | usa a credencial Shopee do perfil ativo |
| `/dashboard/stats`, `/notifications` (`activities`) | contagens/lista do perfil ativo |
| `/users/me/backup`, `/users/me/restore` | exporta/importa só o perfil ativo; backup antigo (sem `profile_id`) e HMAC continuam válidos |
| `request_logs`, `audit_events` | gravam `profile_id`; `GET /logs` (admin) aceita `?profile_id=` opcional |
| `schedulers` + bots (`scheduler/bot_post*.py`) | job guarda o perfil do post; bot usa a credencial/atividades desse perfil |

Migrações: `038_add_profile_id_to_remaining_tables.sql` (coluna nullable + índice + backfill pro perfil principal,
`ON DELETE SET NULL`), `039_relax_unique_for_multi_profile.sql` (remove UNIQUE de `shopee_credentials.app_id`
e troca `UNIQUE (user_id, network)` de `credential_checks` por índice único `(user_id, profile_id, network)`), `041_products_unique_per_profile.sql` (UNIQUE de `products` passa a ser
`(user_id, product_id, perfil)`: o mesmo produto em 2 perfis; duplicado no mesmo perfil = 409) e `042_profile_limit_function_search_path.sql` (define `search_path` da função `enforce_profile_limit()` para evitar mutabilidade).

## Endpoints principais

### Threads OAuth

Fluxo de autorização com Meta para conectar conta Threads (nova implementação em 2026-09-26).

#### `GET /credentials/threads/authorize`

Inicia o fluxo OAuth com Meta.

**Resposta**: Redirect HTTP para URL de consentimento da Meta.

**Uso**: Frontend chama este endpoint que redireciona o usuário para autorizar a app no Meta.

```
GET /credentials/threads/authorize
↓
Redirect: https://www.threads.net/oauth/authorize?client_id=...&redirect_uri=...
```

#### `GET /credentials/threads/callback`

Callback do OAuth — Meta redireciona aqui com o `code` de autorização.

**Parâmetros**:
- `code` (query string) — código de autorização da Meta

**Resposta**: JSON com resultado da troca de código por token ou erro.

```json
{
  "status": "success",
  "message": "Threads connected successfully",
  "network": "threads"
}
```

**Fluxo completo**:
1. Frontend chama `/credentials/threads/authorize`
2. Meta redireciona o usuário para `/credentials/threads/callback?code=...`
3. Callback troca o código por token de acesso e salva no Supabase (criptografado)
4. Usuário é redirecionado para `/panel/credentials` no Flask com sucesso

---

### Proxy de API Transparente (`/api/<path>`)

O Flask expõe um proxy transparente em `/api/<path>` que repassa requisições para a API nova em `127.0.0.1:8001`.

**Implementação**: `web/routes/api_proxy.py` + `web/__init__.py`

**Características**:
- Bypass automático de CSRF (rotas `/api/*` estão isentas)
- Roteamento transparente: cliente sempre fala com `http://localhost:5000/api/...`, Flask roteia internamente
- Headers de autenticação (cookies httpOnly de JWT) são preservados
- Resposta é retornada ao cliente como-é (passthrough)

**Exemplo**:
```
Client: POST http://localhost:5000/api/posts
         ↓ (Flask proxy)
         ↓
FastAPI: POST http://127.0.0.1:8001/posts
         ↓
         → Resposta JSON retornada ao cliente
```

---

## Deploy

### Topologia (2026-09-26)

Ambos os processos (Flask + FastAPI) rodam no **mesmo container Docker**:

- **Gunicorn** (port 8000, 4 workers) serve o Flask
- **Hook `on_starting` do gunicorn** lança uvicorn em background (port 8001)
- **Hook `on_exit` do gunicorn** encerra uvicorn quando gunicorn sai

**Arquivo**: `Dockerfile` + `gunicorn.conf.py`

**Variáveis de ambiente** (necessárias em produção):
```
FLASK_INTERNAL_URL=http://127.0.0.1:8000
INTERNAL_API_SECRET=<shared-secret>
```

O Flask usa `INTERNAL_API_SECRET` para autenticar chamadas HTTP internas do `api/internal_client.py`.

### Topologia futura (pendente)

Quando a API estiver totalmente madura:
- Considerar mover FastAPI para um Web Service separado no Render
- Exigirá compartilhamento de filesystem para mídia (ou storage externo tipo S3)
- Decisão será tomada após validação em produção real

---

## Testing

```bash
# Testes da API
pytest tests/api/

# Cobertura esperada: 80%+
pytest tests/api/ --cov=api --cov-report=term

# Lint
flake8 api/

# Type check (se integrado)
mypy api/
```

---

## Compatibilidade

- **Supabase**: mesmo banco do Flask, RLS mantido
- **Criptografia**: mesma chave/algoritmo Fernet do Flask (`utils/crypto.py`)
- **Scheduler**: chama bridge interno do Flask em vez de importar `scheduler` diretamente (evita dupla ativação)
- **Mídia**: usa mesmo caminho local `web/media/<post_id>/` (requer filesystem compartilhado ou S3)

---

## Referências

- `docs/ROADMAP_MIGRACAO.md` — Fases 0-8 da migração
- `docs/CHECKLIST_MIGRACAO.md` — Checklist e pendências
- `api/requirements.txt` — Dependências
