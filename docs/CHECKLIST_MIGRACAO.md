# Checklist de Migração — React + API Python

> Critério de teste por módulo. Detalhe de cada fase (o que foi feito, o que foi
> simplificado e por quê) está em `docs/ROADMAP_MIGRACAO.md`. Atualizado em 2026-09-14.

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
- [x] CRUD de post único
- [x] Copywriter IA (`/posts/generate-copy`)
- [ ] Thread multi-parte (post encadeado) — não migrado
- [ ] Upload de mídia — não migrado
- [ ] Agendamento/publicação executável pela API nova — não migrado (ver Fase 8)

## Fase 6 — Credenciais
- [x] 6 redes simples (Shopee, X, Facebook, Instagram, TikTok, Kwai) + Threads
- [x] Nunca reexibe valor salvo, só status
- [ ] Validação ao vivo da credencial Shopee contra a API deles — não migrado (Flask ainda faz)
- [ ] Fluxo OAuth do Threads (emitir token) — continua só no Flask

## Fase 7 — Usuários
- [x] CRUD admin-only

## Fase 8 — Scheduler
- [x] Decisão tomada: manter in-process (ADR 19)
- [x] Risco de dupla publicação identificado e documentado (dois processos com `_scheduler` ativo)
- [ ] Caminho de consolidação implementado (expor `add_job`/`remove_job`/`run_job` via HTTP interno do Flask pra API nova chamar)

## Antes de aposentar o Flask (`web/`)
- [ ] Fase 5 com paridade completa (thread, mídia, agendamento)
- [ ] Fase 6 com validação Shopee e fluxo OAuth Threads migrados
- [ ] Scheduler consolidado (Fase 8 pendente)
