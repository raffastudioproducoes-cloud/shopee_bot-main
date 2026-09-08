# Roadmap de Migração — React + API Python

> Em andamento desde 2026-09-04

## Visão geral

Migrar o ShopeeAutoVendas do frontend Flask/Jinja2/Alpine.js para React + TanStack Router + TanStack Query + API Python, mantendo Supabase como banco e Render como deploy.

## Fases da migração

### Fase 0 — Preparação

- [ ] Crio estrutura inicial de pasta: `docs/`, `api/`, `api/routers/`, `scripts/`
- [ ] Documentos criados: `docs/CHECKLIST_MIGRACAO.md`, `docs/ROADMAP_MIGRACAO.md`, `api/README.md`
- [ ] API Python criada como stub (main.py, config.py, database.py, routers/)
- [ ] Frontend React criado como stub (Vite + TS + Tailwind + router + query + zustand)
- [ ] `requirements.txt` novo com dependências FastAPI
- [ ] Atualizo README.md com seção de migração

Fim da fase 0: toda estrutura pronta, é só implementar módulo por módulo.

### Fase 1 — Auth (login/logout, sessão)

- [ ] API Python: router `auth.py` com `/login`, `/logout`, `/me`
- [ ] Frontend React: tela de login, proteção de rotas, auth context/store
- [ ] Testar login/logout com credenciais reais do Supabase

### Fase 2 — Painel/Dashboard

- [ ] API Python: endpoints para contagens (produtos, posts, listas, atividades)
- [ ] Frontend React: dashboard com cards, atividade recente
- [ ] Ícones Lucide React

### Fase 3 — Produtos

- [ ] API Python: CRUD de produtos
- [ ] Frontend React: lista de produtos, form de cadastro/edição
- [ ] Ícones Lucide React

### Fase 4 — Listas de produtos

- [ ] API Python: CRUD de listas de produtos
- [ ] Frontend React: lista de listas, form de criação
- [ ] Ícones Lucide React

### Fase 5 — Posts

- [ ] API Python: CRUD de posts, agendamento, publicação
- [ ] Frontend React: lista de posts, form de criação/edição
- [ ] Copywriter IA: integração com Gemini (ver `apis/llm.py` atual)
- [ ] Ícones Lucide React

### Fase 6 — Credenciais

- [ ] API Python: endpoints para salvar/ler/remover credenciais (cifradas)
- [ ] Frontend React: forms de credencial para cada rede
- [ ] Inputs type=password com value="" (nunca expor valor)
- [ ] Ícones Lucide React

### Fase 7 — Usuários

- [ ] API Python: CRUD de usuários (admin)
- [ ] Frontend React: lista de usuários, form de criação/edição
- [ ] Ícones Lucide React

### Fase 8 — Scheduler (avaliação)

- [ ] Decisão: manter in-process (YAGNI) ou externalizar?
- [ ] Se externalizar: rodar como processo separado no Render

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
