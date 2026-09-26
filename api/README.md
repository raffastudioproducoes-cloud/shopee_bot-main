# API Python — ShopeeAutoVendas

Nova camada de API em FastAPI (async) que roda em background no mesmo container do Flask, acessível via proxy transparente `/api/*` do Flask.

## Arquitetura

- **`api/main.py`** — aplicação FastAPI
- **`api/routers/`** — endpoints organizados por domínio (auth, posts, products, credentials, users)
- **`api/internal_client.py`** — cliente HTTP para chamar bridge interno do Flask (`/internal/*`)
- **`api/database.py`** — acesso ao Supabase via cliente Python async
- **`api/crypto.py`** — criptografia Fernet (compatível com o `utils/crypto.py` do Flask)
- **`tests/api/`** — testes pytest (cobertura 80%+)

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
