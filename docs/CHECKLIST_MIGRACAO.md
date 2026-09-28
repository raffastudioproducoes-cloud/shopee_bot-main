# Checklist de Migração — React + API Python

> Critério de teste por módulo. Detalhe de cada fase (o que foi feito, o que foi
> simplificado e por quê) está em `docs/ROADMAP_MIGRACAO.md`. Atualizado em 2026-09-27.

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
