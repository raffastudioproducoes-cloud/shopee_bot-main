# Checklist de Migração — React + API Python

> Critério de teste por módulo. Detalhe de cada fase (o que foi feito, o que foi
> simplificado e por quê) está em `docs/ROADMAP_MIGRACAO.md`. Atualizado em 2026-09-27; seção final acrescentada em 2026-10-05.

Critérios gerais aplicados a cada módulo abaixo:

- [ ] Renderiza sem erro de console
- [ ] Ícones via Lucide React (sem Material Symbols/Google Fonts)
- [ ] Credenciais nunca expostas de volta em nenhuma resposta da API
- [ ] Requisição à API Python retorna o JSON esperado
- [ ] Persistência no Supabase não muda de comportamento em relação ao Flask
- [ ] `tsc --noEmit` e `vite build` limpos (frontend); `pytest tests/api` e `flake8 api/` limpos (backend)

## Fase 0 — Preparação
- [x] Estrutura de pastas (`api/`, `frontend/`, `docs/`)
- [x] `api/requirements.txt`

## Fase 1 — Auth
- [x] Login/logout via cookie httpOnly (JWT)
- [x] Guard de rota autenticada (`PanelPage`)

## Fase 2 — Painel/Dashboard
- [x] Cards de contagem + ações rápidas

## Fase 3 — Produtos
- [x] CRUD completo, 13 testes (13/13 verde)

## Fase 4 — Listas de produtos
- [x] CRUD completo, produtos associados

## Fase 5 — Posts
- [x] CRUD de post com thread multi-parte
- [x] Copywriter IA (`/posts/generate-copy`)
- [x] Upload de mídia (`/posts/{id}/media`) — só na head da thread
- [x] Agendamento (cron/data) e publicação imediata via bridge interno (Fase 8)

## Fase 6 — Credenciais
- [x] 6 redes simples (Shopee, X, Facebook, Instagram, TikTok, Kwai) + Threads
- [x] Nunca reexibe valor salvo, só status
- [x] Validação ao vivo da credencial Shopee contra a API deles, via bridge interno
- [x] Fluxo OAuth do Threads (emitir token) — migrado pra API nova na Fase 8.1
  (`api/threads_oauth.py`); a rota legada do Flask ainda existe até validar em produção

## Fase 7 — Usuários
- [x] CRUD admin-only

## Fase 8 — Scheduler
- [x] Decisão tomada: manter in-process (ADR 19)
- [x] Risco de dupla publicação identificado e documentado (dois processos com `_scheduler` ativo)
- [x] Bridge interno implementado (`web/routes/internal.py` + `api/internal_client.py`) —
  `add_job`/`remove_job`/`run_job`/`query_auth_validate` expostos via HTTP, secret compartilhado

## Antes de aposentar o Flask (`web/`)
- [x] Topologia de deploy da API nova decidida e implementada no código (2026-09-27):
  mesmo container do Flask (`gunicorn.conf.py` sobe um subprocesso `uvicorn` em
  `127.0.0.1:8001`, proxy `/api/*` em `web/routes/api_proxy.py`) — falta só validar em
  produção no Render, não é mais uma decisão em aberto.
- [ ] `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` configurados em produção (só confirmados
  em dev local até 2026-09-27)
- [x] Fluxo OAuth do Threads migrado pra API nova (`api/threads_oauth.py`, Fase 8.1) — falta
  só aposentar a rota legada do Flask (ver item abaixo) depois de validar em produção

## Pendências reais (2026-09-26)

### Não fazer ainda (validar em produção antes)
- [ ] Aposentar rota legada `/credentials/threads/save?code=` do Flask (`web/routes/panel/credentials.py`
  — usar novo endpoint `/credentials/threads/callback` e `api/threads_oauth.py` após validar em Render)

### Validação em produção
- [ ] Validar em Render que Dockerfile + dois processos (Flask + FastAPI) sobem corretamente
  e se comunicam via bridge interno (`FLASK_INTERNAL_URL` + `INTERNAL_API_SECRET`)
- [ ] Validar que `/api/<path>` proxy funciona em produção sem erros de conectividade interna

### Atualizado 2026-09-27 (cruzado com o código + consulta read-only ao Supabase)
- [x] Wrappers de publicação real para X, Facebook, Instagram, TikTok **já existem**
  (`scheduler/bot_post_x.py`, `bot_post_facebook.py`, `bot_post_instagram.py`,
  `bot_post_tiktok.py`) e estão registrados em `scheduler/__init__.py` — Threads continua
  sendo o único com token de usuário de fato salvo no Supabase.
- [ ] Falta X, Instagram e TikTok terem um usuário passando pelo fluxo "Conectar" (OAuth) —
  app_id/secret estão salvos mas `user_access_token` está nulo nas 3 tabelas (confirmado via
  SQL). Facebook usa token de Página colado manualmente (sem OAuth) e tem credencial
  completa, mas nunca foi validado com sucesso confirmado via "Testar conexão".
- [ ] Botão "Conectar X" ainda não existe no frontend nesta leitura (`CredentialsPage.tsx`
  usa o card genérico sem OAuth para X) — backend (`/credentials/x/authorize` + PKCE) já
  está pronto.

### Issue antiga — já corrigida, não é mais um bug conhecido
- [x] ~~`api/routers/posts.py` chama `supabase.table(...)` diretamente, mas `supabase` em
  `api/database.py` seria uma função, não uma instância~~ — **já corrigido**: `api/database.py`
  define `_SupabaseProxy` (objeto lazy com `__getattr__` delegando pra `get_supabase()`),
  então `supabase.table(...)` funciona normalmente. Confirmado lendo o código em 2026-09-27.

## Atualizado 2026-10-05 — multi-perfil completo (branch `chore/phase-12-integration`)

> Nota datada: as seções acima registram o estado de 2026-09-27 e foram mantidas. O que mudou
> desde então (evidência: `git log main..HEAD`, `database/migrations/037-042`):

- [x] Perfis por conta (até 3), com trigger de limite no banco (migração 037)
- [x] `profile_id` nas 14 tabelas restantes (migração 038), relaxamento de UNIQUE (039) e índice único com coalesce (040);
  migrações do repositório vão até a 041
- [x] Posts, mídias, credenciais das redes, dashboard, notificações, catálogo, logs, backup/restore
  e bots do scheduler escopados pelo perfil ativo
- [x] UI de perfis: editar, excluir, ativar sem reload, perfil ativo na TopBar; `GET /auth/me` devolve `profile_id`
- [x] Segurança: JWT invalidado na troca de senha (`pwv`), validação do `profile_id` do token,
  rate limit em criar perfil/backup/restore
- [x] Infra: Dockerfile não-root + `HEALTHCHECK`, gunicorn `timeout = 120` com supervisão do uvicorn
- [x] CI: flake8 bloqueante, job `frontend`, Python 3.13, cache, `concurrency`; CD via `workflow_run`; dependabot e template de PR
- [ ] Ainda pendente (ações manuais de Rafa, não são código) — atualizado 2026-10-05:
  - [x] Env vars do serviço `shopee-bot-staging` no Render (copiar as de produção) — confirmado pelo Rafa, 2026-10-05.
  - [x] Trocar o branch de produção do serviço no Render de `master` para `main` — confirmado pelo Rafa, 2026-10-05.
  - [x] Secret `RENDER_STAGING_DEPLOY_HOOK_URL` no GitHub — confirmado pelo Rafa, 2026-10-05.
  - [x] Cadastrar as callback URLs de cada rede (X, Meta, TikTok) nos painéis de desenvolvedor — confirmado pelo Rafa, 2026-10-05.
  - [x] Conectar X, Instagram e TikTok (ação humana: clicar "Conectar" e autorizar) e recolar o Client Secret do TikTok — confirmado pelo Rafa, 2026-10-05.
  - [ ] Branch protection: exige GitHub Pro ou repositório público (GitHub Free não oferece em repo privado) — GitHub Pro ativo (confirmado pelo Rafa, 2026-10-05), mas branch protection ainda não configurada (possível agora, ainda não ativada).
  - [ ] Aplicar as migrações 037, 038, 039, 040, 041 e 042 no Supabase (ver `docs/RULES.md` item 11). Disco/permissão do container não-root: o Dockerfile já cria e dá `chown app` a `/shopee_bot/upload` e `/shopee_bot/web/media` (únicos pontos de escrita local; mídia vai para disco, avatar para Supabase Storage). Pendência só se o Render montar disco persistente: ver `docs/RULES.md` item 11.
  - [ ] Merge dos PRs da branch `chore/phase-12-integration` em `main`.
