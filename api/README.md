# API Python — Shopee Auto Vendas

> API backend em Python (FastAPI) para o frontend React migrado.
> Consome o Supabase existente.

## Estrutura do diretorio

O diretorio `api/` contem:

- `main.py` — aplicacao FastAPI com CORS e health check
- `config.py` — configuracoes via variaveis de ambiente
- `database.py` — cliente Supabase
- `routers/` — roteadores de recurso
  - `__init__.py` — marca pacote
  - `auth.py` — login, logout, perfil
  - `users.py` — CRUD de usuarios
  - `products.py` — CRUD de produtos
  - `posts.py` — CRUD de posts, agendamento, publicação
  - `credentials.py` — credenciais cifradas
- `requirements.txt` — dependencias da API
- `.env.example` — exemplo de variaveis de ambiente

## Instalacao

```bash
cd api
pip install -r requirements.txt
```

## Execucao

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Variaveis de ambiente

- `SUPABASE_URL` — URL do projeto Supabase
- `SUPABASE_KEY` — API key (service role ou anon)
- `CORS_ORIGINS` — origens permitidas pelo CORS (padrao: frontend React)
- `API_SECRET_KEY` — chave secreta da API (opcional, para assinatura de tokens)

## Endpoints principais

- `GET /health` — health check
- `POST /auth/login` — login
- `POST /auth/logout` — logout
- `GET /auth/me` — usuario logado
- `GET /users` — lista paginada
- `POST /users` — cria usuario
- `PUT /users/{id}` — atualiza
- `DELETE /users/{id}` — remove
- `GET /products` — lista paginada
- `POST /products` — cria produto
- `PUT /products/{id}` — atualiza
- `DELETE /products/{id}` — remove
- `GET /posts` — lista paginada
- `POST /posts` — cria post
- `PUT /posts/{id}` — atualiza
- `DELETE /posts/{id}` — remove
- `POST /posts/{id}/publish` — publica agora
- `GET /credentials/{network}/{user_id}` — ler credencial
- `PUT /credentials/{network}/{user_id}` — salvar credencial cifrada
- `DELETE /credentials/{network}/{user_id}` — remover

## Seguranca

- CORS restrito a origem do frontend
- Sessao via token JWT ou cookie seguro
- Credentials cifradas com Fernet (se necessario)

## Coexistencia com Flask

Durante a migracao, a API Python roda em paralelo com o Flask atual (`web/`). O frontend React aponta para a nova API. O Flask continua sendo usado pelos templates Jinja2 remanescentes ate a migracao estar completa.
