# Roadmap de Migração — React + API Python

> Em andamento desde 2026-09-04. Atualizado em 2026-09-14 — Fases 0-7 concluídas
> (Fase 5 com escopo simplificado, ver nota). Fase 8 decidida.

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

- [x] API Python: CRUD de post único (`api/routers/posts.py`)
- [x] Copywriter IA: integração com Gemini (`apis/llm.py`, endpoint `/posts/generate-copy`)
- [x] Frontend React: lista de posts, modal de criação/edição, seleção de produtos, botão "Gerar texto com IA"
- [x] Ícones Lucide React

**Escopo simplificado nesta fase** (ver `api/routers/posts.py` docstring):
- **Sem encadeamento em thread** (o Flask permite post multi-parte via `posts.post_id`
  auto-referenciado; a API nova cria só posts avulsos, `post_id` sempre `NULL`).
- **Sem upload de mídia** (o Flask sobe pra `web/media/<post_id>/`, cifra pro Cloudinary
  na publicação — não replicado).
- **Sem agendamento/publicação executável pela API nova.** `add_job`/`remove_job`/`run_job`
  (`scheduler/__init__.py`) dependem de um singleton `_scheduler` em memória, inicializado
  uma vez por processo gunicorn (Flask). Rodar `scheduler.init()` também no processo FastAPI
  arriscaria dois schedulers ativos ao mesmo tempo em produção → post publicado em duplicata.
  Agendar/publicar continua exclusivamente pelo painel Flask até a Fase 8 decidir a
  consolidação. Ver nota na Fase 8.

### Fase 6 — Credenciais

- [x] API Python: `api/routers/credentials.py` — salvar/ler status/remover, 5 redes simples
  (Shopee, X, Facebook, Instagram, TikTok, Kwai) + Threads (OAuth, formato próprio)
- [x] Frontend React: card por rede, nunca reexibe o valor salvo (só status conectado/desconectado)
- [x] Secret cifrado com `utils.crypto.encrypt` (mesma chave/algoritmo do Flask — compatível)
- [x] Ícones Lucide React

**Escopo simplificado**: a Shopee valida a credencial ao vivo contra a API deles antes de
salvar (`apis/shopee.py:query_auth_validate`) no Flask; a API nova salva sem validar (igual
já fazem as outras 5 redes hoje). Threads continua exigindo o fluxo OAuth do Flask pra emitir
o token — o formulário novo só aceita colar um token já emitido.

### Fase 7 — Usuários

- [x] API Python: `api/routers/users.py` — CRUD admin-only (gate por `access == "ADMIN"`)
- [x] Frontend React: tabela de usuários, modal de criação/edição, item de nav só pra admin
- [x] Ícones Lucide React

### Fase 8 — Scheduler (decisão)

- [x] **Decisão: manter in-process** (reafirma o ADR `19-ADR-Scheduler-In-Process.md` —
  YAGNI, sem tráfego que justifique um worker externo).
- [x] **Achado durante a Fase 5**: rodar `scheduler.init()` em dois processos (Flask +
  FastAPI) simultaneamente arrisca dois `_scheduler` (APScheduler) ativos publicando o
  mesmo job — duplicata em produção. Enquanto os dois processos coexistirem, **só o Flask
  deve chamar `scheduler.init()`**.
- [ ] **Pendente** (bloqueia aposentar o Flask): mover agendamento/publicação para a API
  nova. Caminho mais simples — sem introduzir um segundo processo scheduler: expor
  `add_job`/`remove_job`/`run_job` (que já são funções Python puras, não Flask-specific)
  como endpoints HTTP internos no Flask, e o FastAPI chamá-los via HTTP em vez de importar
  o módulo `scheduler` diretamente. Alternativa mais trabalhosa: migrar o processo Flask
  inteiro pra rodar só como o "scheduler worker", sem servir páginas.

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
