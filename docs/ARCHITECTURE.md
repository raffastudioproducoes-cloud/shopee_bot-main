# ARCHITECTURE — Shopee Auto Vendas

> Documento canônico vivo. Cenário A (projeto existente). Toda afirmação técnica abaixo foi
> verificada lendo o código real do repositório em 2026-09-29. Itens sem evidência direta
> estão marcados **[A CONFIRMAR COM O USUÁRIO]**.

## 1. Visão geral dos componentes

O projeto está em **migração incremental**: um frontend/backend legado (Flask + Jinja2 +
Alpine.js) roda em produção hoje, enquanto um frontend/backend novo (React + FastAPI) é
construído em paralelo e já cobre as mesmas funcionalidades. Ambos coexistem no mesmo
container Docker.

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Container Docker (Render)                    │
│                                                                     │
│  ┌───────────────┐   proxy /api/*   ┌──────────────────────────┐ │
│  │  Flask (web/)  │ ───────────────▶ │ FastAPI (api/) — uvicorn │ │
│  │  Gunicorn:8000 │                  │      127.0.0.1:8001       │ │
│  │  Jinja2+Alpine │                  │  routers/ auth,posts,     │ │
│  │  (legado, produção)               │  products,lists,users,    │ │
│  │                │ ◀─── bridge ──── │  credentials,notifications│ │
│  │                │   HTTP interno   │                            │ │
│  │  scheduler.init()│  (X-Internal-Secret) └──────────────────────┘ │
│  └───────┬────────┘                              │                 │
│          │                                       │                 │
│          ▼                                       ▼                 │
│   APScheduler (in-process, jobstore Postgres)     │                 │
│          │                                       │                 │
└──────────┼───────────────────────────────────────┼─────────────────┘
           │                                       │
           ▼                                       ▼
     Supabase (Postgres, RLS)               Frontend React (build
                                             estático servido pelo
                                             Flask via web/routes/spa.py)
```

Fonte: `Dockerfile`, `gunicorn.conf.py`, `web/routes/api_proxy.py`, `api/internal_client.py`,
`web/routes/internal.py`.

## 2. Stack real

| Camada | Tecnologia | Função |
| --- | --- | --- |
| Frontend legado (produção) | Flask 3.x + Jinja2 + Alpine.js + Tailwind CSS (build local) | Painel atual do usuário |
| Frontend novo (em migração) | React 19 + TypeScript estrito + Vite 6 + TanStack Router + TanStack Query + Zustand + Tailwind CSS v4 + Lucide React | Novo painel, substitui o Jinja gradualmente |
| Backend legado | Flask 3.x, Flask-Login, Flask-WTF, Flask-Limiter, Flask-CORS | Rotas `web/routes/panel/`, ainda em produção |
| Backend novo | FastAPI (async), Pydantic-settings | Rotas `api/routers/`, roda em subprocesso uvicorn no mesmo container |
| Scheduler | APScheduler 3.11, jobstore `SQLAlchemyJobStore` sobre Postgres | Jobs de publicação e atualização de produto, in-process |
| Banco | Supabase (Postgres gerenciado), RLS habilitado em todas as tabelas, acesso via `psycopg` (não `supabase-py` no lado Flask) e cliente Python async no lado FastAPI | Persistência |
| Mídia | Cloudinary (host temporário) | Upload/hospedagem de imagem de post |
| IA | Google Gemini (`apis/llm.py`) | Copywriter de post por persona |
| Cripto | `cryptography` (Fernet) — `utils/crypto.py` (Flask) e `api/crypto.py` (wrapper compatível, FastAPI) | Cifra credencial de rede social em repouso |
| Infra/Deploy | Render (Web Service, Docker, plano Free), GitHub Actions (CI) | Deploy automático a cada push em `master` |
| WSGI/ASGI | Gunicorn + gevent (Flask), Uvicorn (FastAPI) | Servidores de aplicação |

## 3. Estrutura de pastas real

```text
shopee_bot-main/
├── api/                     # API nova (FastAPI), roda em paralelo ao Flask
│   ├── main.py              # app FastAPI
│   ├── config.py            # pydantic-settings (SUPABASE_URL/KEY etc.)
│   ├── database.py          # _SupabaseProxy — acesso lazy ao Supabase
│   ├── crypto.py            # Fernet, compatível com utils/crypto.py do Flask
│   ├── internal_client.py   # chama o bridge HTTP interno do Flask
│   ├── middleware.py
│   ├── {threads,x,tiktok,instagram,facebook}_oauth.py  # OAuth de app único por rede
│   └── routers/
│       ├── auth.py          # login/logout/register — cadastro público força access="USER"
│       ├── credentials.py   # SIMPLE_NETWORKS (Shopee/Kwai) x OAUTH_NETWORKS (as 5 outras)
│       ├── posts.py         # CRUD de post, thread, upload de mídia, copy IA
│       ├── products.py
│       ├── lists.py
│       ├── users.py         # admin-only
│       ├── dashboard.py
│       └── notifications.py
├── apis/                    # wrappers de API de terceiros (Shopee, Threads, X, TikTok, Facebook, Instagram, llm)
├── database/                # acesso ao Postgres/Supabase usado pelo Flask legado
│   └── migrations/          # SQL numerado sequencialmente
├── scheduler/                # APScheduler in-process
│   ├── bot_post.py           # Threads (original)
│   ├── bot_post_x.py
│   ├── bot_post_facebook.py
│   ├── bot_post_instagram.py
│   ├── bot_post_tiktok.py
│   └── update_products.py
├── web/                      # Flask legado, ainda em produção
│   ├── routes/
│   │   ├── panel/            # credentials.py, profile.py
│   │   ├── api_proxy.py      # proxy transparente /api/<path> -> FastAPI interno
│   │   ├── internal.py       # bridge HTTP interno (add_job/remove_job/run_job/query_auth_validate)
│   │   └── spa.py            # serve o build do React
│   ├── templates/, static/, media/
├── frontend/                  # React novo
│   └── src/
│       ├── pages/             # DashboardPage, LoginPage, PanelPage, PostsPage, ProductsPage, ListasPage, CredentialsPage, UsersPage
│       ├── components/ui/     # design system (ver DESIGN.md)
│       ├── api/                # clientes HTTP tipados
│       ├── stores/              # Zustand (auth)
│       └── styles/tokens/       # colors/typography/fonts/spacing/radius/elevation/motion
├── docs/                       # documentação da migração e docs canônicos (este arquivo)
├── vault/                       # ponteiro pro vault Obsidian (não duplica conteúdo)
└── tests/
    └── api/                     # testes da API FastAPI, isolados do conftest do Flask
```

## 4. Fluxo OAuth "app único" (peça arquitetural mais distintiva)

Para Threads, X, TikTok, Instagram e Facebook: **um único app** é registrado no painel de
desenvolvedor de cada rede (por Rafa/dono do SaaS), com `client_id`/`client_secret` vindos de
variável de ambiente (`api/x_oauth.py`, `api/tiktok_oauth.py`, `api/instagram_oauth.py`,
`api/threads_oauth.py`, `api/facebook_oauth.py`). O usuário final nunca vê nem cola essas
credenciais — só clica "Conectar [rede]" e autoriza. Shopee e Kwai não têm OAuth público e
seguem o modelo manual (usuário cola App ID/Secret do próprio Portal de Afiliados).

```mermaid
sequenceDiagram
    participant U as Usuário (browser)
    participant F as Flask (proxy /api/*)
    participant A as FastAPI (api/routers/credentials.py)
    participant R as Rede social (Meta/X/TikTok)
    participant DB as Supabase

    U->>F: GET /api/credentials/{rede}/authorize
    F->>A: proxy transparente (bypass CSRF)
    A->>A: monta authorize_url com client_id do ENV (app único)
    A-->>U: 302 Redirect para R (tela de consentimento)
    U->>R: Autoriza o app único
    R-->>U: 302 Redirect para /api/credentials/{rede}/callback?code=...
    U->>F: GET /api/credentials/{rede}/callback
    F->>A: proxy transparente
    A->>R: POST troca code por access_token (client_secret do ENV)
    R-->>A: access_token (+ refresh_token quando aplicável)
    A->>A: cifra o token (Fernet, api/crypto.py)
    A->>DB: salva em {rede}_credentials.user_access_token
    A-->>U: redirect para /panel/credentials com sucesso
```

**Estado real (2026-09-29)**: o fluxo acima está implementado nas 5 redes, mas só o
**Threads** tem um `access_token` de fato salvo no Supabase para o único usuário de
produção — as outras quatro (X, Instagram, TikTok, Facebook) têm o app único configurado e a
UI de "Conectar" pronta, porém ninguém completou o handshake ainda (ver `docs/MEMORY.md`).

## 5. Bridge interno Flask ↔ FastAPI

A API nova não importa `scheduler`/`apis.shopee` diretamente — chama por HTTP interno
(`api/internal_client.py` → `web/routes/internal.py`), autenticado por segredo compartilhado
(`X-Internal-Secret`, isento de CSRF). Motivo documentado no código: rodar
`scheduler.init()` em dois processos simultâneos arriscaria duas instâncias do APScheduler
ativas publicando o mesmo job em duplicata — por isso **só o Flask** chama
`scheduler.init()`; a API nova pede `add_job`/`remove_job`/`run_job`/`query_auth_validate`
via bridge.

## 6. Segurança (arquitetural)

- Credenciais de rede social cifradas em repouso (Fernet, chave `APP_ENCRYPTION_KEY`, com
  rotação/fallback documentados no `README.md`).
- Rate limiting (Flask-Limiter) nas rotas de credenciais e login.
- CSRF global (Flask-WTF) exceto para `/api/*` (proxy, bypass documentado).
- CSP, X-Frame-Options, HSTS configurados.
- Handler de exceção genérico em produção (não vaza traceback).
- Cookie de sessão `Secure; HttpOnly; SameSite=Lax`.

## 7. Decisões arquiteturais registradas (ADRs no vault)

- **Scheduler in-process** (não separar em worker) — `19-ADR-Scheduler-In-Process.md`
  (vault). Gatilho de revisão: hospedagem de produção real de fato ativa, volume de posts
  crescer, ou necessidade de múltiplas instâncias simultâneas.
- **Coexistência Flask+FastAPI no mesmo container** em vez de dois Web Services separados no
  Render — decisão tomada por custo/complexidade (Fase 8.1 do roadmap de migração).
- **App único de OAuth** (substituindo o modelo per-user anterior para X/TikTok/Instagram) —
  detalhe completo em `27-Migracao-App-Unico-OAuth.md` (vault).

## Referências

- `README.md`, `api/README.md`, `docs/ROADMAP_MIGRACAO.md`
- Vault Obsidian: `02-Arquitetura-e-Tecnologias.md`, `arquiteturas.md`,
  `07-Diagrama-de-Arquitetura.md`, `19-ADR-Scheduler-In-Process.md`,
  `27-Migracao-App-Unico-OAuth.md`, `26-Deploy-Render.md`
