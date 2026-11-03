> **Auto Orbital — F4C1 em desenvolvimento (03/11/2026):** cotas de posts imediatos e horários recorrentes por plano/perfil preparadas na branch `feature/f4c1-publication-quotas-20261103`. Migration SQL 073 aplicada com autorização e registrada após verificação de RLS/roles; código da PR #215 ainda não implantado. A F4B anterior (migração 072, PR #214) já está LIVE somente em staging; `main`/produção mantém a versão 3.0.0. Ver [contrato F4](docs/PLANOS-F4-POLITICAS-E-FASES-20261103.md) e `CHANGELOG.md`.

> **Entrada obrigatória para agentes e IAs:** leia primeiro [AGENTS.md](AGENTS.md) e o [Guia Mestre de Contexto](docs/GUIA-MESTRE-IA.md) — propósito, localização do Vault, arquitetura, módulos, fluxos, APIs, segurança, RLS, custos, limites e método de verificação. Documentos históricos não substituem o código implantado.\n\n<div align="center">

> **Homologação de posts, 02/11/2026:** PR [#186](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/186) implementa geração de uma descrição de IA por rede, limites validados e avisos de compatibilidade de mídia. Somente staging, sem publicação real de teste; [detalhes](docs/POSTS-COPY-IA-POR-REDE-20261102.md).

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

> **Em migração**: o Flask (`web/`) segue no mesmo container servindo o proxy `/api/*`,
> o scheduler e o build do React; o painel Jinja legado fica desligado por padrão
> (`LEGACY_PANEL_ENABLED=false`) e o painel principal é o React (`frontend/`). Ver
> [Roadmap da migração](#roadmap-da-migração).

**Versão atual:** `3.0.0` (fonte oficial: [`VERSION`](VERSION), histórico: [`CHANGELOG.md`](CHANGELOG.md)). Esta atualização consolida as alterações incompatíveis do fluxo de posts: um produto por publicação e criação somente em `Agora` ou `Recorrente`. Inclui descrições de IA por rede, rascunhos persistentes, identificadores `#ID`, melhorias de concorrência e histórico de ocorrências. `2.7.0` introduziu até cinco horários diários de recorrência e o tratamento/reencodificação de MP4. O processamento de vídeo permanece sem scanner antivírus isolado (ver `docs/POST-MEDIA-SECURITY.md`).

**Em homologação (somente `staging`, ainda fora da versão 3.0.0 de produção):** página `Criar POST` dedicada e modo de prévia de campanha por lista, com ordem de produtos e calendário; a prévia não ativa publicações. Ver [documentação da campanha](docs/CAMPANHA-POR-LISTA-PREVIA-20261103.md) e o bloco `[Não lançado]` do `CHANGELOG.md`. O ícone do menu usa Lucide `square-pen` registrado no design system.

**Governança de versão e deploy:** cada PR de código deve adicionar seu resumo em `[Não lançado]`. Só após homologação e autorização do proprietário uma PR `staging` → `main` promove o lote e atualiza `VERSION` e changelog conforme SemVer (próxima MINOR compatível candidata: `3.1.0`). Não confundir merge em `staging` com release pública.

**Histórico anterior:** `2.6.0` (15/10/2026) trouxe painel administrativo, métricas/capacidade, separação cliente/`/admin` e overrides de credenciais. `2.5.0` adicionou splash, esqueletos de carregamento e correções de segurança. `2.4.0` (14/10/2026) aplicou a identidade AUTO ORBITAL, PWA, Ajuda/FAQ, documentos legais e callbacks Meta/Threads. O app Meta segue condicionado à aprovação da plataforma; X continua desabilitado pela regra do produto e TikTok foto é melhoria futura. O histórico de integração multi-perfil permanece preservado em `CHANGELOG.md`.

**Limitações de validação:** deploy/CI e autenticação não substituem teste externo de publicação; Threads 403 continua sob acompanhamento. `staging` e `main` usam o mesmo Supabase, e a decisão posterior de centralizar os disparos na produção demanda ajuste técnico próprio. O acesso de revisão `RafaelTesteCliente` deve ser preservado.

## Objetivo

Tirar o trabalho manual de quem divulga produto de afiliado:

- **garimpar** produto elegível (comissão, vendas, categoria) sem sair do painel;
- **gerar copy** com IA (Gemini) por persona, sem escrever do zero toda vez;
- **publicar agora ou programar recorrência**, com acompanhamento de ocorrências, falhas e resultados incertos;
- **organizar** produtos em listas reaproveitáveis entre posts;
- **conectar credenciais** de cada rede social de forma cifrada, nunca expostas de volta na tela;
- **acompanhar** o que foi feito por atividade, com histórico auditável.

## Funcionalidades principais

| Módulo | Recursos |
| --- | --- |
| **Garimpo** | Busca de produtos na Shopee Open API por categoria, palavra-chave, comissão mínima e vendas |
| **Produtos** | Cadastro, edição, listagem com busca — origem manual ou vinda do garimpo. Aba "Pesquisa Avançada" busca em tempo real no catálogo da Shopee (API de afiliados), com filtros e importação direta pro catálogo pessoal |
| **Listas de produtos** | Agrupamento de produtos reaproveitável entre posts |
| **Posts** | Criação de post com um produto, publicação imediata ou recorrente (até 7 dias, até cinco horários diários), histórico de ocorrências e tratamento de resultados incertos. Preview e variantes por rede com mídia privada e adaptação conforme compatibilidade; sucesso real depende de OAuth/escopos e teste na rede. |
| **Copywriter IA** | Geração de texto de post por persona com a chave de IA do próprio usuário (Gemini, OpenAI ou Anthropic — Credenciais; `apis/llm.py`) |
| **Credenciais** | Shopee, Threads, X, Facebook, Instagram, TikTok, Kwai — cifradas em repouso (Fernet), nunca reexibidas |
| **Atividades** | Histórico auditável de ações do usuário |
| **Perfis e Configurações** | Até 3 perfis por conta (1 principal + 2 secundários, com avatar), editar/excluir/ativar sem recarregar a página e perfil ativo na TopBar; Shopee, assistente/IA e catálogo de produtos são compartilhados pela conta. Listas, posts, mídias, credenciais sociais, dashboard operacional, notificações, logs e backup/restore usam o perfil ativo (ver [Multi-perfil](#multi-perfil)). Página `/settings` com troca de senha. Administração de acesso (ADMIN/USER) na página Perfis |
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
- **Render** (Web Service, Docker) — Python 3.13 (build do frontend em Node 22 no `Dockerfile`); a imagem roda como usuário não-root e tem `HEALTHCHECK` em `/health`
- **GitHub Actions** — CI (lint, testes da API e build do frontend) e CD (ver [Deploy](#deploy))

## Estrutura do projeto

```text
shopee_bot-main/
├── api/                    # API nova (FastAPI) — em migração
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── requirements.txt
│   └── routers/            # auth, profiles, settings, products, lists, posts,
│                           # credentials, users, dashboard, notifications, catalog, logs
├── frontend/               # Frontend novo (React + Vite) — em migração
│   ├── src/
│   │   ├── api/            # clientes HTTP tipados por recurso
│   │   ├── lib/            # cliente HTTP base
│   │   ├── pages/          # Dashboard, Login, Panel, Products, Listas, Posts, Credentials, Profiles, Settings
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

Requisitos: Python 3.13 (versão usada pela CI e pelo `Dockerfile`), Node.js 20+, conta Supabase (ou Postgres local via `docker-compose-dev.yml`).

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
# API nova (FastAPI) — isolada do conftest do Flask, não precisa de Postgres.
# É exatamente o que a CI roda.
python -m pytest tests/api --confcutdir=tests/api -q

# Lint bloqueante da CI (erros de sintaxe/nomes indefinidos em api/)
flake8 api/ --select=E9,F63,F7,F82

# Frontend: type check + build (também roda na CI; não há testes de frontend)
cd frontend && npm ci && npm run build

# Flask legado (precisa de Postgres local em localhost:5433 — ver conftest.py);
# NÃO roda na CI
pytest tests/test_auth_root.py tests/test_publish.py
```

> `--confcutdir=tests/api` é necessário: o `conftest.py` da raiz faz
> `gevent.monkey.patch_all()` (Flask legado), que trava as threads
> async do `anyio`/`httpx` usadas pelo `TestClient` do FastAPI.

## Deploy

- **Plataforma**: Render (Web Service, Docker), plano Free.
- **Build**: lê o `Dockerfile` da raiz (Python 3.13-slim + gunicorn + gevent).
- **CI** (`.github/workflows/ci.yml`, push/PR em `main`): job `api` (flake8 bloqueante + `pytest tests/api`, Python 3.13) e job `frontend` (`npm ci` + `npm run build`, Node 20); cache de pip/npm e `concurrency` por ref.
- **CD** (`.github/workflows/cd.yml`): dispara via `workflow_run` só quando a CI termina com sucesso em `main` (push) e chama o deploy hook do Render (secret `RENDER_DEPLOY_HOOK_URL`; sem o secret, o job emite warning e pula). `.github/dependabot.yml` (semanal) e `.github/pull_request_template.md` complementam o fluxo.
- **Fluxo de branches**: Git Flow (`main` produção, `staging` homologação, `feature/*`); ver `docs/RULES.md`. GitHub Pro está ativo (confirmado pelo Rafa, 2026-10-05); branch protection agora é possível, mas ainda não configurada.
- **Pendências em produção** (confirmado pelo Rafa, 2026-10-05): env vars do Render (`shopee-bot-staging`), branch de produção de `master` para `main`, callback URLs das redes, conectar redes sociais — ver `docs/TASK.md` item 10.13.
- **Auto-deploy**: integração nativa do Render com o GitHub, a cada push em `main` (serviço de produção `shopee-bot` já na branch `main`, verificado em 2026-10-06 via API do Render).
- **Banco**: Supabase, via Session Pooler (IPv4 — o Direct Connection só responde IPv6, incompatível com o Render Free).

Detalhes de infraestrutura e histórico de bugs resolvidos no deploy: Vault `26-Deploy-Render.md`.

### Variáveis de ambiente

A lista completa, com comentário de cada uma e valores placeholder, está em `.env-example`.
Principais grupos: Supabase (`SUPABASE_URL`, `SUPABASE_KEY`), JWT da API (`API_SECRET_KEY`),
Postgres do Flask/scheduler (`SHOPEE_PG_*`), bridge interno (`INTERNAL_API_SECRET`,
`FLASK_INTERNAL_URL`, `API_INTERNAL_URL`), OAuth de app único (`THREADS_*`, `X_CLIENT_ID/SECRET`,
`INSTAGRAM_*`, `FACEBOOK_*`, `TIKTOK_CLIENT_KEY/SECRET`, mais as `*_CALLBACK_URL`),
criptografia (`APP_ENCRYPTION_KEY`), mídia (bucket privado `post-media` no Supabase Storage, sem credencial de CDN externo) (IA: chave por usuário em Credenciais),
`FRONTEND_URL`, `CORS_ORIGINS` e `REQUEST_LOGGING_ENABLED`. Nunca versionar valores reais.

### Processo no container

`gunicorn.conf.py` usa `timeout = 120` e sobe o uvicorn (FastAPI) em subprocesso com um
supervisor que o reinicia com backoff se ele cair.

## Banco de dados

Supabase (Postgres), schema com RLS habilitado em todas as tabelas:
`users`, `profiles`, `products`, `product_lists`, `product_lists_products`, `posts`,
`medias`, `posts_medias`, `posts_products`, `schedulers`, `apscheduler_jobs`,
`activities`, `activity_types`, `audit_events`, `request_logs`, `credential_checks`,
`migrations`, e uma tabela de credenciais por rede (`shopee_credentials`,
`threads_credentials`, `x_credentials`, `facebook_credentials`, `instagram_credentials`,
`tiktok_credentials`, `kwai_credentials`).

Migrações SQL numeradas em `database/migrations/` (hoje até a `042`), rodadas em sequência no
boot (`run_migrations`) e registradas na tabela `migrations`. Migração aplicada direto no
Supabase precisa ser registrada à mão — ver `docs/RULES.md` item 9. **Migrações 037, 038, 039, 040, 041 e 042 já foram aplicadas no Supabase (2026-10-06)** — verificado via MCP; registradas em `public.migrations`. Ver `docs/RULES.md` item 11 para procedimento e risco conhecido.

### Multi-perfil

Cada conta tem até 3 perfis (1 principal + 2 secundários), limite imposto também no banco por
trigger (migração 037). O perfil ativo vai no claim `profile_id` do JWT; o backend valida que o
perfil pertence ao usuário e, se não pertencer, cai no perfil principal. `GET /auth/me` devolve
o `profile_id` ativo e o frontend o lê de lá (sem `localStorage`). `profile_id` existe em 16
tabelas (036: `products`, `product_lists`; 038: as outras 14, com índice e backfill para o
perfil principal) com `ON DELETE SET NULL`. A 039 removeu o UNIQUE de `shopee_credentials.app_id`;
a 040 adiciona índice único com coalesce para deduplicar NULLs em `credential_checks`
e trocou o de `credential_checks` por `(user_id, profile_id, network)`. A 041 troca o UNIQUE `(product_id, user_id)` de `products` por `(user_id, product_id, perfil)`: o mesmo
produto pode existir em 2 perfis (duplicado no mesmo perfil = 409). Backup/restore e os bots
do scheduler também respeitam o perfil.

## Segurança

- Credenciais de rede social cifradas em repouso (Fernet, com rotação de chave e fallback)
- Rate limiting nas rotas de credenciais e no login
- CSRF global (Flask-WTF) + Content-Security-Policy, X-Frame-Options, HSTS
- Handler de exceção genérico em produção (não vaza traceback)
- Cookie de sessão `Secure; HttpOnly; SameSite=Lax`
- JWT da API invalidado na troca de senha (claim `pwv`); tokens antigos sem o claim continuam aceitos
- Rate limit também em criar perfil, backup e restore
- Container roda como usuário não-root

Para reportar uma vulnerabilidade, ver `SECURITY.md`.

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

## Autenticação Supabase — preparação em PR #149 (01/11/2026)

O login por e-mail e Google, o cadastro com nome de usuário/e-mail/senhas iguais/aceite, a confirmação obrigatória de e-mail e a recuperação de senha por link estão em desenvolvimento na branch `feature/supabase-auth-email-google`. A nova UI de recuperação pede e-mail e permite definir nova senha somente após o link do Supabase Auth. A senha não é alterada na tabela comercial `public.users`.

**Ainda não foi implantado em produção.** Não ativar `SUPABASE_AUTH_ENABLED` antes de migrar com segurança as duas contas legadas, testar recuperação e confirmação reais, avaliar sessões internas e resolver a entrega a e-mails de clientes externos (Supabase SMTP padrão é limitado a membros da equipe). Consulte [docs/SUPABASE-AUTH-MIGRACAO.md](docs/SUPABASE-AUTH-MIGRACAO.md).

## Documentação

| Documento | Conteúdo |
| --- | --- |
| `docs/CHECKLIST_MIGRACAO.md` | Checklist da migração para React + FastAPI, por módulo |
| `docs/ROADMAP_MIGRACAO.md` | Roadmap detalhado da migração |
| `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md` | Decisão aprovada em 2026-10-13: marca futura **Auto Orbital**; implementação ainda pendente |
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
- [x] **Fase 5** — Posts (thread multi-parte, mídia, agendamento, publicação, copywriter IA)
- [x] **Fase 6** — Credenciais (forms sem expor valor, 6 redes + Threads, validação Shopee ao vivo)
- [x] **Fase 7** — Usuários (admin-only)
- [x] **Fase 8** — Scheduler: decidido manter in-process; consolidado via bridge HTTP interno (`web/routes/internal.py`) — ver `docs/ROADMAP_MIGRACAO.md`
- [x] **Fase 8.1** — Consolidação final: FastAPI sobe como subprocesso `uvicorn` no MESMO container do Flask (`gunicorn.conf.py`), proxy transparente `/api/*` (`web/routes/api_proxy.py`), OAuth do Threads migrado pra API nova (`api/threads_oauth.py`), coluna `network` em `posts` pra publicar em várias redes
- [ ] Aposentar o Flask (`web/`) — a topologia de deploy já está implementada no código (mesmo container); falta validar isso em produção no Render e confirmar `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` lá

**Publicação real por rede** (verificado em 2026-09-27, cruzando código + Supabase — ver
`vault/00-INDICE-Estado-Atual.md` no Vault Obsidian para o detalhe): os wrappers de
publicação de Threads, X, Facebook, Instagram e TikTok existem e estão registrados no
scheduler. Threads é o único com token de usuário conectado de fato hoje — X, Instagram e
TikTok têm app registrado (app_id/secret) mas ninguém completou o OAuth ("Conectar") ainda;
Facebook usa um token de Página colado manualmente e tem credencial completa, mas nunca foi
validado com sucesso confirmado. Kwai fica de fora (sem API pública confirmada).

## Licença

Software proprietário © Raffa Studio Produções. Uso, cópia, modificação ou
distribuição somente com autorização expressa do titular.

## Contato

**Raffa Studio Produções**
E-mail: **contato.raffasp@gmail.com**
