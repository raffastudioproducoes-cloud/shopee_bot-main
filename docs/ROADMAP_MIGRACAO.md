# Roadmap de Migração — React + API Python

> Em andamento desde 2026-09-04. Atualizado em 2026-09-26 — Fases 0-8 concluídas.
> Próxima etapa: validar deploy em produção (Render) e aposentar rota OAuth legada do Flask.
> Wrappers de publicação das 5 redes sociais sendo implementados em paralelo.

## Visão geral

Migrar o ShopeeAutoVendas do frontend Flask/Jinja2/Alpine.js para React + TanStack Router + TanStack Query + API Python, mantendo Supabase como banco e Render como deploy.

## Fases da migração

### Fase 0 — Preparação

- [x] Estrutura inicial de pasta: `docs/`, `api/`, `api/routers/`, `scripts/`
- [x] Documentos criados: `docs/CHECKLIST_MIGRACAO.md`, `docs/ROADMAP_MIGRACAO.md`, `api/README.md`
- [x] API Python criada (main.py, config.py, database.py, routers/)
- [x] Frontend React criado (Vite + TS + Tailwind + router + query + zustand)
- [x] `api/requirements.txt` com dependências FastAPI
- [x] README.md com seção de migração

### Fase 1 — Auth (login/logout, sessão)

- [x] API Python: router `auth.py` com `/login`, `/logout`, `/me` (JWT em cookie httpOnly)
- [x] Frontend React: tela de login, proteção de rotas (guard em `PanelPage`), auth store (Zustand)
- [x] Testado end-to-end contra Supabase

### Fase 2 — Painel/Dashboard

- [x] Frontend React: dashboard com cards de contagem, ações rápidas
- [x] Ícones Lucide React

### Fase 3 — Produtos

- [x] API Python: CRUD de produtos (13 testes, 13/13 verde)
- [x] Frontend React: lista de produtos, form de cadastro/edição
- [x] Ícones Lucide React

### Fase 4 — Listas de produtos

- [x] API Python: CRUD de listas de produtos
- [x] Frontend React: lista de listas, form de criação
- [x] Ícones Lucide React

### Fase 5 — Posts

- [x] API Python: CRUD de post com thread multi-parte (`api/routers/posts.py`)
- [x] Copywriter IA: integração com Gemini (`apis/llm.py`, endpoint `/posts/generate-copy`)
- [x] Agendamento (cron/data) e publicação imediata via bridge interno (ver Fase 8)
- [x] Upload de mídia (`POST /posts/{id}/media`, mesmo caminho `web/media/<post_id>/` do Flask)
- [x] Frontend React: lista de posts, modal com partes de thread, upload/remoção de mídia,
  seletor "Agora / Data específica / Recorrente", botão "publicar agora", "Gerar texto com IA"
- [x] Ícones Lucide React

**Simplificações restantes** (ver `api/routers/posts.py` docstring):
- Upload de mídia só na head da thread, não em cada parte.
- Publicação de verdade hoje só existe pra Threads (`func="bot_post"`) — as outras 5 redes
  têm credencial mas nenhum wrapper de publicação ligado ao scheduler ainda (isso é
  limitação do Flask original, não da migração).
- Upload de mídia grava no filesystem local do processo da API nova — só funciona de
  verdade em produção quando ela roda no mesmo container/filesystem que o Flask (ver
  Fase 8; hoje só o Flask está deployado no Render).

### Fase 6 — Credenciais

- [x] API Python: `api/routers/credentials.py` — salvar/ler status/remover, 5 redes simples
  (Shopee, X, Facebook, Instagram, TikTok, Kwai) + Threads (OAuth, formato próprio)
- [x] Validação ao vivo da credencial Shopee contra a API deles antes de salvar, via bridge
  interno (`web/routes/internal.py:validate_shopee`) — paridade com o Flask
- [x] Frontend React: card por rede, nunca reexibe o valor salvo (só status conectado/desconectado)
- [x] Secret cifrado com `api/crypto.py` (mesma chave/algoritmo Fernet do `utils/crypto.py`
  do Flask — compatível; wrapper próprio pra não arrastar deps do Flask pro `api/requirements.txt`)
- [x] Ícones Lucide React

**Escopo simplificado que fica**: Threads continua exigindo o fluxo OAuth do Flask pra emitir
o token (troca de código com a Meta) — o formulário novo só aceita colar um token já emitido.

### Fase 7 — Usuários

- [x] API Python: `api/routers/users.py` — CRUD admin-only (gate por `access == "ADMIN"`)
- [x] Frontend React: tabela de usuários, modal de criação/edição, item de nav só pra admin
- [x] Ícones Lucide React

### Fase 8 — Scheduler (decisão + consolidação)

- [x] **Decisão: manter in-process** (reafirma o ADR `19-ADR-Scheduler-In-Process.md` —
  YAGNI, sem tráfego que justifique um worker externo).
- [x] **Achado durante a Fase 5**: rodar `scheduler.init()` em dois processos (Flask +
  FastAPI) simultaneamente arrisca dois `_scheduler` (APScheduler) ativos publicando o
  mesmo job — duplicata em produção. Enquanto os dois processos coexistirem, **só o Flask
  deve chamar `scheduler.init()`**.
- [x] **Consolidado via bridge interno**: `web/routes/internal.py` expõe
  `add_job`/`remove_job`/`run_job` e `query_auth_validate` (Shopee) como endpoints HTTP
  protegidos por segredo compartilhado (`X-Internal-Secret`, isento de CSRF); a API nova
  chama por HTTP (`api/internal_client.py`) em vez de importar `scheduler`/`apis.shopee`
  diretamente. `create_post`/`delete_post` na API nova já usam isso pra agendar/desagendar.

### Fase 8.1 — Consolidação final (2026-09-26)

Implementadas as 5 mudanças finais para suportar a API nova em produção:

- [x] **1. Dockerfile + gunicorn.conf.py + api/internal_client.py** (2026-09-26)
  - FastAPI novo sobe como processo uvicorn em background no MESMO container Flask
  - Hook `on_starting`/`on_exit` do gunicorn gerencia o ciclo de vida
  - **Por quê**: evita precisar de um Web Service Render separado; reduz custos e complexidade de orquestração de dois serviços
  - Status: Implementado e testado localmente (sem Docker disponível — validar em produção)

- [x] **2. web/routes/api_proxy.py + web/__init__.py** (2026-09-26)
  - Flask agora tem proxy transparente `/api/<path>` que repassa pro FastAPI interno (`127.0.0.1:8001`)
  - Bypass automático de CSRF para endpoints `/api/*`
  - **Por quê**: encapsula a topologia interna; cliente frontend sempre fala com Flask, Flask roteia
  - Status: Implementado

- [x] **3. api/threads_oauth.py + endpoints OAuth em api/routers/credentials.py** (2026-09-26)
  - Fluxo OAuth do Threads agora existe na API nova (async)
  - `GET /credentials/threads/authorize` → redirect pra Meta
  - `GET /credentials/threads/callback` → troca código por token
  - Testes em `tests/api/test_threads_oauth.py`
  - **Por quê**: preparação para eventual aposentadoria do Flask; isola lógica OAuth numa camada
  - Status: Implementado

- [x] **4. Frontend React (frontend/src/pages/CredentialsPage.tsx)** (2026-09-26)
  - Botão "Conectar Threads" chamando novo endpoint `/credentials/threads/authorize`
  - **Por quê**: integração do frontend com a API nova
  - Status: Implementado

- [x] **5. database/migrations/023_add_network_to_posts.sql** (2026-09-26)
  - Coluna `network` adicionada em `posts`
  - Mapa `network→func` em `database/schedulers.py` e `api/routers/posts.py`
  - Seletor de rede no form de criação de post (Flask legado e React)
  - **Por quê**: suportar múltiplas redes sociais em paralelo; escolher qual publicar por post
  - Status: Implementado

- [ ] **Pendente real** (bloqueia aposentar o Flask): hoje só o Flask está deployado no
  Render — a API nova (`api/`) ainda não tem processo próprio em produção, então
  `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` só existem em dev local. Falta decidir a
  topologia de deploy (mesmo container? Web Service separado no Render?) antes do bridge
  funcionar em produção. Mídia (Fase 5) tem a mesma dependência (filesystem compartilhado).

## Documentação criada nesta sessão

- `docs/CHECKLIST_MIGRACAO.md` — checklist de migração por módulo
- `docs/ROADMAP_MIGRACAO.md` — este arquivo (roadmap de migração)
- `api/README.md` — documentação da nova API Python
- `scripts/README.md` — scripts de utilidade

## Estado atual (2026-09-04)

- [x] Rollback do trabalho de UI anterior
- [x] Estrutura de pastas criada: `docs/`, `api/`, `api/routers/`, `scripts/`
- [x] Documentos criados: checklist, roadmap, api/README
- [ ] API Python stub criado (main.py, config.py, database.py, routers/)
- [ ] Frontend React stub criado (Vite + TS + Tailwind + router + query + zustand)
- [ ] `requirements.txt` atualizado com dependências da API
- [ ] README.md atualizado com seção de migração

## Próximos passos

1. Criar API Python stub (`main.py`, `config.py`, `database.py`, routers/)
2. Criar frontend React stub (Vite + TS + Tailwind + TanStack Router + TanStack Query + Zustand)
3. Atualizar README.md com seção de migração
4. Commit + push da estrutura inicial
5. Iniciar migração do módulo Auth

## Referências

- Supabase existente: migração já feita, tabelas e RLS mantidos
- `apis/llm.py` — cópia do copywriter IA atual (Gemini) para referência da nova API
- `apis/` — wrappers de API de redes sociais existentes (Shopee, Threads, etc)
- `database/` — módulos de acesso ao banco existentes (para reutilizar se necessário)

## Rollback

Para cada módulo: branch `migrate/<modulo>` a partir de `master`. Se algo falhar, voltar para `master` e remover a branch do módulo.
