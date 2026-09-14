<div align="center">

# Shopee Auto Vendas

### Divulgação automática de afiliado, do garimpo ao post.

[![React](https://img.shields.io/badge/React-19-06B6D4?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vite.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![Render](https://img.shields.io/badge/Render-deploy-46E3B7?logo=render&logoColor=white)](docs/ROADMAP_MIGRACAO.md)
[![License](https://img.shields.io/badge/license-proprietary-0F172A)](#licença)

</div>

---

## Sumário

1. [Apresentação](#apresentação)
2. [Objetivo](#objetivo)
3. [Funcionalidades principais](#funcionalidades-principais)
4. [Tecnologias](#tecnologias)
5. [Estrutura do projeto](#estrutura-do-projeto)
6. [Instalação](#instalação)
7. [Desenvolvimento](#desenvolvimento)
8. [Build](#build)
9. [Testes](#testes)
10. [Deploy](#deploy)
11. [Banco de dados](#banco-de-dados)
12. [Segurança](#segurança)
13. [Processo do projeto (ciclo operacional)](#processo-do-projeto-ciclo-operacional)
14. [Documentação](#documentação)
15. [Roadmap da migração](#roadmap-da-migração)
16. [Licença](#licença)
17. [Contato](#contato)

---

## Apresentação

**Shopee Auto Vendas** é uma plataforma que automatiza a divulgação de links de
afiliado da Shopee (e, em expansão, de outras redes sociais). Um único painel
cobre o fluxo inteiro: garimpar produto na Shopee Open API, gerar o texto do
post com IA, agendar ou publicar na hora, e acompanhar tudo pelo histórico de
atividades.

Hospedado em **Render (Free)**: `https://shopee-bot-fj0w.onrender.com`.
Banco: **Supabase** (Postgres gerenciado).

> **Em migração**: o frontend em produção hoje é Flask + Jinja2 + Alpine.js
> (funcional, mantido enquanto a migração roda). O novo frontend React já está
> em construção em paralelo — ver [Roadmap da migração](#roadmap-da-migração).

## Objetivo

Tirar o trabalho manual de quem divulga produto de afiliado:

- **garimpar** produto elegível (comissão, vendas, categoria) sem sair do painel;
- **gerar copy** com IA (Gemini) por persona, sem escrever do zero toda vez;
- **agendar ou publicar na hora**, com retry e log de falha — sem post perdido silenciosamente;
- **organizar** produtos em listas reaproveitáveis entre posts;
- **conectar credenciais** de cada rede social de forma cifrada, nunca expostas de volta na tela;
- **acompanhar** o que foi feito por atividade, com histórico auditável.

## Funcionalidades principais

| Módulo | Recursos |
| --- | --- |
| **Garimpo** | Busca de produtos na Shopee Open API por categoria, palavra-chave, comissão mínima e vendas |
| **Produtos** | Cadastro, edição, listagem com busca — origem manual ou vinda do garimpo |
| **Listas de produtos** | Agrupamento de produtos reaproveitável entre posts |
| **Posts** | Criação, agendamento (cron/data), publicação sob demanda, retry e log de falha |
| **Copywriter IA** | Geração de texto de post via Gemini, por persona (`apis/llm.py`) |
| **Credenciais** | Shopee, Threads, X, Facebook, Instagram, TikTok, Kwai — cifradas em repouso (Fernet), nunca reexibidas |
| **Atividades** | Histórico auditável de ações do usuário |
| **Usuários** | Administração de acesso (ADMIN/USER) |
| **Scheduler** | Jobs agendados in-process (APScheduler, jobstore em Postgres) — ADR em `19-ADR-Scheduler-In-Process.md` (Vault) |

## Tecnologias

**Frontend em produção hoje** (Flask + Jinja2):
- Flask 3.x + Jinja2 + Alpine.js, Tailwind CSS (build local, sem CDN)
- Gunicorn + gevent, deploy via Docker no Render

**Frontend novo** (em migração, ver [Roadmap](#roadmap-da-migração)):
- **React 19** + **TypeScript** estrito
- **Vite 6** + **TanStack Router** + **TanStack Query**
- **Tailwind CSS v4**
- **Zustand** (estado de auth)
- **Lucide React** (ícones — substitui Material Symbols via Google Fonts, que falhava no Render)

**Backend / API**:
- **FastAPI** (nova API em `api/`, coexistindo com o Flask atual durante a migração)
- Flask (rotas legadas em `web/`, ainda em produção)
- **Supabase** (Postgres) via Session Pooler
- Credenciais cifradas com **Fernet**

**Infra**:
- **Render** (Web Service, Docker) — deploy automático a partir do GitHub
- **GitHub Actions** — CI (lint + testes da API Python)

## Estrutura do projeto

```text
shopee_bot-main/
├── api/                    # API nova (FastAPI) — em migração
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   └── routers/
│       ├── auth.py
│       ├── products.py
│       └── lists.py
├── frontend/               # Frontend novo (React + Vite) — em migração
│   ├── src/
│   │   ├── api/            # clientes HTTP tipados por recurso
│   │   ├── lib/            # cliente HTTP base
│   │   ├── pages/          # Dashboard, Login, Panel, Products, Listas
│   │   ├── stores/         # Zustand (auth)
│   │   └── router.tsx      # TanStack Router (code-based)
│   └── vite.config.ts
├── web/                    # Frontend em produção hoje (Flask + Jinja2)
│   ├── routes/
│   ├── templates/
│   └── static/
├── apis/                   # wrappers das redes sociais (Shopee, Threads, X, ...)
├── database/               # acesso ao Postgres/Supabase (usado pelo Flask)
├── scheduler/              # APScheduler in-process
├── docs/                   # documentação da migração
├── tests/
│   └── api/                # testes da API FastAPI (isolados do conftest do Flask)
└── .github/workflows/      # CI (ci.yml) e trigger de deploy (cd.yml)
```

## Instalação

```bash
git clone https://github.com/raffastudioproducoes-cloud/shopee_bot-main.git
cd shopee_bot-main

# Flask (produção atual)
python -m venv .venv
.venv/Scripts/activate       # Windows; source .venv/bin/activate no Linux/Mac
pip install -r requirements.txt

# API nova (FastAPI)
pip install -r api/requirements.txt

# Frontend novo (React)
cd frontend && npm install
```

Requisitos: Python 3.11+, Node.js 20+, conta Supabase (ou Postgres local via `docker-compose-dev.yml`).

## Desenvolvimento

```bash
# Flask (produção atual) — http://localhost:5000
python -m flask --app shopee_bot.web run --debug

# API nova (FastAPI) — http://localhost:8000
uvicorn api.main:app --reload

# Frontend novo (React) — http://localhost:5173, proxy /api -> :8000
cd frontend && npm run dev
```

## Build

```bash
cd frontend
npm run build       # tsc + vite build -> frontend/dist/
```

O Flask (`web/`) não tem build separado — Jinja2 é renderizado em runtime.

## Testes

```bash
# Flask (precisa de Postgres local em localhost:5433 — ver conftest.py)
pytest tests/test_auth.py tests/test_publish.py

# API nova (FastAPI) — isolada do conftest do Flask, não precisa de Postgres
python -m pytest tests/api --confcutdir=tests/api
```

> `--confcutdir=tests/api` é necessário: o `conftest.py` da raiz faz
> `gevent.monkey.patch_all()` (Flask legado), que trava as threads
> async do `anyio`/`httpx` usadas pelo `TestClient` do FastAPI.

## Deploy

- **Plataforma**: Render (Web Service, Docker), plano Free.
- **Build**: lê o `Dockerfile` da raiz (Python 3.13-slim + gunicorn + gevent).
- **Auto-deploy**: integração nativa do Render com o GitHub, a cada push em `master`.
- **Banco**: Supabase, via Session Pooler (IPv4 — o Direct Connection só responde IPv6, incompatível com o Render Free).

Detalhes de infraestrutura, variáveis de ambiente e histórico de bugs resolvidos no deploy: Vault `26-Deploy-Render.md`.

## Banco de dados

Supabase (Postgres), schema com RLS habilitado em todas as tabelas:
`users`, `products`, `product_lists`, `product_lists_products`, `posts`,
`medias`, `posts_medias`, `posts_products`, `schedulers`, `apscheduler_jobs`,
`activities`, `activity_types`, `migrations`, e uma tabela de credenciais por
rede (`shopee_credentials`, `threads_credentials`, `x_credentials`,
`facebook_credentials`, `instagram_credentials`, `tiktok_credentials`,
`kwai_credentials`).

## Segurança

- Credenciais de rede social cifradas em repouso (Fernet, com rotação de chave e fallback)
- Rate limiting nas rotas de credenciais e no login
- CSRF global (Flask-WTF) + Content-Security-Policy, X-Frame-Options, HSTS
- Handler de exceção genérico em produção (não vaza traceback)
- Cookie de sessão `Secure; HttpOnly; SameSite=Lax`

## Processo do projeto (ciclo operacional)

```text
Garimpo (Shopee Open API)
        ↓
Cadastro de produto (manual ou do garimpo)
        ↓
Lista de produtos (opcional, agrupamento)
        ↓
Criação de post (copy manual ou gerado por IA)
        ↓
Agendamento ou publicação imediata
        ↓
Scheduler executa → publica na rede social
        ↓
Log de sucesso/falha + Atividade registrada
```

## Documentação

| Documento | Conteúdo |
| --- | --- |
| `docs/CHECKLIST_MIGRACAO.md` | Checklist da migração para React + FastAPI, por módulo |
| `docs/ROADMAP_MIGRACAO.md` | Roadmap detalhado da migração |
| `api/README.md` | Endpoints, variáveis de ambiente e coexistência da nova API |
| Vault `00-INDICE-Estado-Atual.md` | Fonte viva de estado do projeto (ler antes de qualquer sessão) |
| Vault `26-Deploy-Render.md` | Infra de deploy, variáveis de ambiente, bugs resolvidos |
| Vault `21-Relatorio-Correcoes-Seguranca-2026-08-21.md` | Detalhe das correções de segurança aplicadas |

## Roadmap da migração

Migração por módulos, testando cada um antes de avançar:

- [x] **Fase 0** — estrutura (API stub, frontend stub)
- [x] **Fase 1** — Auth (login/logout, sessão via cookie)
- [x] **Fase 2** — Painel/Dashboard
- [x] **Fase 3** — Produtos (CRUD completo, 13 testes)
- [x] **Fase 4** — Listas de produtos
- [ ] **Fase 5** — Posts (criação, agendamento, publicação, copywriter IA)
- [ ] **Fase 6** — Credenciais (forms sem expor valor)
- [ ] **Fase 7** — Usuários
- [ ] **Fase 8** — Scheduler (decidir: manter in-process ou externalizar)
- [ ] Aposentar o Flask (`web/`) depois que todas as fases acima estiverem no ar

## Licença

Software proprietário © Raffa Studio Produções. Uso, cópia, modificação ou
distribuição somente com autorização expressa do titular.

## Contato

**Raffa Studio Produções**
E-mail: **contato.raffasp@gmail.com**
