# API Python — Shopee Auto Vendas

> API backend em Python (FastAPI) para o frontend React migrado.
> Consome o Supabase existente.

## Estrutura

```
api/
├── main.py         # FastAPI app
├── config.py       # variáveis de ambiente
├── database.py     # conexão com Supabase
├── routers/
│   ├── __init__.py
│   ├── auth.py     # login, logout, me
│   ├── users.py    # CRUD usuarios
│   ├── products.py # CRUD produtos
│   ├── posts.py    # CRUD posts, agendamento, publicação
│   └── credentials.py # credenciais cifradas
├── __init__.py
└── requirements.txt
```

## Instalação

```bash
cd api
pip install -r requirements.txt
```

## Execução

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Variáveis de ambiente

- `SUPABASE_URL` — URL do projeto Supabase
- `SUPABASE_KEY` — API key (service role ou anon)
- `CORS_ORIGINS` — origens permitidas pelo CORS (padrão: frontend React)

## Endpoints principais

- `GET /health` — health check
- `POST /auth/login` — login
- `POST /auth/logout` — logout
- `GET /auth/me` — usuário logado
- `GET /users` — lista paginada
- `POST /users` — cria usuário
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

## Segurança

- CORS restrito à origem do frontend
- Sessão via token JWT ou cookie seguro
- Credentials cifradas com Fernet (se necessário)

## Coexistência com Flask

Durante a migração, a API Python roda em paralelo com o Flask atual (`web/`). O frontend React aponta para a nova API. O Flask continua sendo usado pelos templates Jinja2 remanescentes até a migração estar completa.
