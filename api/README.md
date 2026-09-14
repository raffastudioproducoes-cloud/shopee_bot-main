# API Python — Shopee Auto Vendas

> API backend em Python (FastAPI) para o frontend React migrado.
> Consome o Supabase existente. Coexiste com o Flask (`web/`) durante a migração.

## Estrutura do diretório

- `main.py` — aplicação FastAPI, CORS, health check, registro dos routers
- `config.py` — configurações via variáveis de ambiente (pydantic-settings)
- `database.py` — cliente Supabase (`supabase-py`)
- `routers/`
  - `auth.py` — login/logout/perfil (JWT em cookie httpOnly)
  - `products.py` — CRUD de produtos
  - `lists.py` — CRUD de listas de produtos
  - `posts.py` — CRUD de post único + copywriter IA (sem thread/mídia/agendamento — ver docstring do módulo e `docs/ROADMAP_MIGRACAO.md`)
  - `credentials.py` — credenciais cifradas (6 redes simples + Threads)
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
- `APP_ENCRYPTION_KEY` — chave Fernet (mesma do Flask) usada por `utils.crypto` pra cifrar/decifrar credenciais

## Endpoints

- `GET /health`
- `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `GET|POST /products`, `GET|PUT|DELETE /products/{id}`
- `GET|POST /lists`, `GET|PUT|DELETE /lists/{id}`
- `GET|POST /posts`, `GET|PUT|DELETE /posts/{id}`, `POST /posts/generate-copy`
- `GET /credentials` (status de todas as redes)
- `PUT|DELETE /credentials/{network}` (`shopee`, `x`, `facebook`, `instagram`, `tiktok`, `kwai`)
- `PUT|DELETE /credentials/threads` (rota literal — ver comentário no router sobre ordem de registro)
- `GET|POST /users`, `GET|PUT|DELETE /users/{id}` (admin-only)

Doc interativa: `/docs` (Swagger) e `/redoc` quando a API está rodando.

## Segurança

- CORS restrito à origem do frontend
- Sessão via JWT em cookie `httpOnly`
- Credenciais cifradas com Fernet (`utils.crypto`, mesma chave do Flask)
- `/credentials` nunca devolve o valor salvo — só `{"connected": bool}`

## Import de `utils`/`apis` (pacotes na raiz do repo)

`utils/__init__.py` e módulos de `apis/` fazem parte do código original do Flask e às
vezes importam `shopee_bot.*` — um alias de pacote que só existe nativamente no layout
do Docker (`WORKDIR /shopee_bot`). `utils/__init__.py` registra esse alias sozinho quando
não existe (mesmo truque do `conftest.py` da raiz), então `utils.crypto` funciona tanto
no Flask quanto na API nova. Módulos de `apis/` que dependem de `shopee_bot.*` diretamente
(ex.: `apis/shopee.py`) **não** foram testados a partir da API nova — evite importá-los
daqui sem verificar antes.

## Coexistência com Flask

O Flask continua sendo o site em produção (`web/`) e é quem chama `scheduler.init()` —
agendamento e publicação de posts continuam só por ele. A API nova ainda não expõe isso
(ver Fase 8 em `docs/ROADMAP_MIGRACAO.md`: rodar `scheduler.init()` em dois processos ao
mesmo tempo arrisca publicar em duplicata).
