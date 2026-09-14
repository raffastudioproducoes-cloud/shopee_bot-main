# API Python — Shopee Auto Vendas

> API backend em Python (FastAPI) para o frontend React migrado.
> Consome o Supabase existente. Coexiste com o Flask (`web/`) durante a migração.

## Estrutura do diretório

- `main.py` — aplicação FastAPI, CORS, health check, registro dos routers
- `config.py` — configurações via variáveis de ambiente (pydantic-settings)
- `database.py` — cliente Supabase (`supabase-py`)
- `crypto.py` — wrapper Fernet próprio (mesma chave/algoritmo do `utils/crypto.py` do
  Flask, sem importar o pacote `utils` — evita arrastar deps do Flask pro `api/requirements.txt`)
- `internal_client.py` — cliente HTTP pro bridge interno do Flask (agendamento/
  publicação/validação Shopee — ver `web/routes/internal.py` e Fase 8 do roadmap)
- `routers/`
  - `auth.py` — login/logout/perfil (JWT em cookie httpOnly)
  - `products.py` — CRUD de produtos
  - `lists.py` — CRUD de listas de produtos
  - `posts.py` — CRUD de post com thread multi-parte, copywriter IA, upload de mídia,
    agendamento/publicação (via bridge interno) — ver docstring do módulo
  - `credentials.py` — credenciais cifradas (6 redes simples + Threads), valida Shopee
    ao vivo via bridge interno
  - `users.py` — CRUD de usuários (admin-only)
- `requirements.txt` — dependências da API

## Instalação

```bash
pip install -r api/requirements.txt
```

## Execução

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Variáveis de ambiente

- `SUPABASE_URL` — URL do projeto Supabase
- `SUPABASE_KEY` — API key (service role ou anon)
- `CORS_ORIGINS` — origens permitidas pelo CORS (padrão: frontend React em dev)
- `API_SECRET_KEY` — assina o JWT do cookie de sessão
- `APP_ENCRYPTION_KEY` — chave Fernet (mesma do Flask) usada por `crypto.py` pra cifrar/decifrar credenciais
- `FLASK_INTERNAL_URL` — URL do Flask, do ponto de vista da API nova (bridge interno)
- `INTERNAL_API_SECRET` — segredo compartilhado com o Flask pro bridge interno (mesmo valor nos dois processos)

## Endpoints

- `GET /health`
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `GET|POST /products`, `GET|PUT|DELETE /products/{id}`
- `GET|POST /lists`, `GET|PUT|DELETE /lists/{id}`
- `GET|POST /posts`, `GET|PUT|DELETE /posts/{id}`, `POST /posts/generate-copy`
- `POST /posts/{id}/publish` (publicação imediata)
- `POST /posts/{id}/media` (multipart), `DELETE /posts/{id}/media/{media_id}`
- `GET /credentials` (status de todas as redes)
- `PUT|DELETE /credentials/{network}` (`shopee`, `x`, `facebook`, `instagram`, `tiktok`, `kwai`)
- `PUT|DELETE /credentials/threads` (rota literal — ver comentário no router sobre ordem de registro)
- `GET|POST /users`, `GET|PUT|DELETE /users/{id}` (admin-only)

Doc interativa: `/docs` (Swagger) e `/redoc` quando a API está rodando.

## Segurança

- CORS restrito à origem do frontend
- Sessão via JWT em cookie `httpOnly`
- Credenciais cifradas com Fernet (`crypto.py`, mesma chave do Flask)
- `/credentials` nunca devolve o valor salvo — só `{"connected": bool}`
- Chamadas ao Flask (bridge interno) autenticadas por segredo compartilhado, nunca por
  sessão de browser

## Coexistência com Flask

O Flask continua sendo o site em produção (`web/`) e é quem chama `scheduler.init()` —
agendamento e publicação de posts, e validação ao vivo da Shopee, passam por
`web/routes/internal.py` (bridge HTTP, ver Fase 8 em `docs/ROADMAP_MIGRACAO.md`: rodar
`scheduler.init()` em dois processos ao mesmo tempo arriscaria publicar em duplicata).

Upload de mídia grava em `web/media/<post_id>/` — o mesmo caminho relativo do Flask.
Só funciona de verdade em produção quando os dois processos compartilham filesystem;
hoje só o Flask está deployado no Render, então isso é dev-local-only até a topologia
de deploy da API nova ser decidida.
