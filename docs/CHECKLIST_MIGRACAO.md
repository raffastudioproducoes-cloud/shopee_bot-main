# Checklist de Migração — React + API Python

> Critério de teste por módulo. Detalhe de cada fase (o que foi feito, o que foi
> simplificado e por quê) está em `docs/ROADMAP_MIGRACAO.md`. Atualizado em 2026-09-26.

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
- [ ] Fluxo OAuth do Threads (emitir token) — continua só no Flask

## Fase 7 — Usuários
- [x] CRUD admin-only

## Fase 8 — Scheduler
- [x] Decisão tomada: manter in-process (ADR 19)
- [x] Risco de dupla publicação identificado e documentado (dois processos com `_scheduler` ativo)
- [x] Bridge interno implementado (`web/routes/internal.py` + `api/internal_client.py`) —
  `add_job`/`remove_job`/`run_job`/`query_auth_validate` expostos via HTTP, secret compartilhado

## Antes de aposentar o Flask (`web/`)
- [ ] Decidir topologia de deploy da API nova em produção (mesmo container do Flask,
  pra compartilhar filesystem/rede interna, ou Web Service separado no Render)
- [ ] `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` configurados em produção
- [ ] Fluxo OAuth do Threads migrado (Fase 6, único item de credenciais que resta)

## Pendências reais (2026-09-26)

### Não fazer ainda (validar em produção antes)
- [ ] Aposentar rota legada `/credentials/threads/save?code=` do Flask (`web/routes/panel/credentials.py`
  — usar novo endpoint `/credentials/threads/callback` e `api/threads_oauth.py` após validar em Render)

### Validação em produção
- [ ] Validar em Render que Dockerfile + dois processos (Flask + FastAPI) sobem corretamente
  e se comunicam via bridge interno (`FLASK_INTERNAL_URL` + `INTERNAL_API_SECRET`)
- [ ] Validar que `/api/<path>` proxy funciona em produção sem erros de conectividade interna

### Em andamento (implementado por outros agentes em paralelo)
- [ ] Wrappers de publicação real para X, Facebook, Instagram, TikTok
  (Threads já está funcional; os outros 4 têm credencial mas nenhum wrapper ligado ao scheduler)

### Issues conhecidas (não corrigido, é outra tarefa)
- [ ] **Bug pré-existente**: `api/routers/posts.py` chama `supabase.table(...)` diretamente,
  mas `supabase` em `api/database.py` é uma função (retorna a instância), não uma instância.
  Isso quebraria em runtime em qualquer rota autenticada de posts.
  **Fix**: renomear a função `supabase()` para algo como `get_supabase_client()` ou criar um 
  singleton/cache se há overhead na chamada.
