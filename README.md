# Shopee Auto Vendas

Automação de divulgação de links de afiliado da Shopee e redes sociais.

## Sobre

Plataforma para:
- Cadastrar produtos e listas de produtos da Shopee
- Agendar posts (cron/data) e publicar sob demanda
- Conectar credenciais de redes sociais de forma cifrada
- Acompanhar atividades e histórico

Hospedado em **Render (Free)** em `https://shopee-bot-fj0w.onrender.com` com Supabase como banco.

## Stack em transição

**Frontend atual (Jinja2 + Alpine.js):**
- Flask 3.x + Jinja2 templates + Alpine.js
- Material Symbols (Google Fonts) para ícones — problemático no Render (CDN etc)

**Nova stack (migração iniciada 2026-09-04):**

| Camada | Tecnologia |
|--------|------------|
| Frontend | React 19 + TypeScript + TanStack Router + TanStack Query + Vite + Tailwind CSS + Zustand |
| Backend API | Python 3.13 + FastAPI (nova API coexistindo com Flask durante migração) |
| Banco | Supabase (estrutura de tabelas mantida) |
| Deploy | Render (mantido) |

### Por que migrar

- Material Symbols via Google Fonts falha no Render (CDN externo) → ícones aparecem como texto
- Jinja2 + Alpine.js limita manutenção, testes e escalabilidade
- React + Vite + Tailwind entrega build consistente, hot reload, testes, deploy previsível
- Nova API Python serve frontend React com JSON, mantendo Supabase estruturalmente inalterado

## Migração (em andamento desde 2026-09-04)

A migração será feita **por módulos**, testando cada um antes de avançar, com **rollback por módulo** (branch `migrate/<modulo>`).

### Módulos (ordem)

1. **Auth** — login/logout, sessão
2. **Painel/Dashboard** — cards com contagens, atividade
3. **Produtos** — lista, cadastro, edição
4. **Listas de produtos** — relação muitos-para-muitos
5. **Posts** — criação, agendamento, execução, copywriter IA
6. **Credenciais** — forms de credencial (inputs password sem expor valor)
7. **Usuários** — listagem administrativa
8. **Scheduler** — avaliar manter in-process (YAGNI ADR) ou externalizar

### Critérios de teste por módulo

- Renderiza sem erros de console
- Ícones aparecem corretamente (Lucide React, sem Material Symbols)
- Credenciais não expostas nos inputs
- Requisições à API Python funcionam e retornam JSON esperado
- Persistência no Supabase não muda de comportamento
- Deploy no Render mantém funcionamento

### Rollback por módulo

Antes de cada módulo:
1. `git checkout -b migrate/<modulo> master`
2. Trabalhar no módulo
3. Se ok: `git checkout master && git merge migrate/<modulo> && git push`
4. Se falhar: `git checkout master && git branch -D migrate/<modulo>`

### Documentação da migração

- `docs/CHECKLIST_MIGRACAO.md` — checklist por módulo com critérios de teste
- `docs/ROADMAP_MIGRACAO.md` — roadmap detalhado da migração
- `api/README.md` — documentação da nova API Python (endpoints, stack, vars de ambiente, coexistência)

## Estrutura do repositório (pós-migração)

```
shopee_bot-main/
├── api/
│   ├── README.md          # docs da nova API
│   ├── main.py            # FastAPI app
│   ├── config.py          # variáveis de ambiente
│   ├── database.py        # conexão Supabase
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       ├── users.py
│       ├── products.py
│       ├── posts.py
│       └── credentials.py
├── frontend/              # projeto Vite + React (criar na migração)
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   ├── components/
│   │   ├── lib/
│   │   └── stores/
│   ├── index.html
│   └── vite.config.ts
├── docs/
│   ├── CHECKLIST_MIGRACAO.md
│   └── ROADMAP_MIGRACAO.md
├── web/                   # Flask atual (até a migração completa)
│   ├── routes/
│   ├── templates/
│   ├── static/
│   └── __init__.py
├── apis/                  # wrappers de API de redes sociais (Shopee, Threads, etc)
├── database/              # acesso ao BD (PostgreSQL/Supabase)
├── scheduler/             # APScheduler (jobstore em Postgres)
├── tests/
└── scripts/               # scripts utilitários
```

## API Python (nova)

Documentação completa em `api/README.md`. Endpoints:

### Auth
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### Health
- `GET /health`

### Users (admin)
- `GET /users` (paginated)
- `GET /users/{id}`
- `POST /users`
- `PUT /users/{id}`
- `DELETE /users/{id}`

### Products
- `GET /products` (paginated)
- `GET /products/{id}`
- `POST /products`
- `PUT /products/{id}`
- `DELETE /products/{id}`

### Posts
- `GET /posts` (paginated)
- `GET /posts/{id}`
- `POST /posts`
- `PUT /posts/{id}`
- `DELETE /posts/{id}`
- `POST /posts/{id}/publish`

### Product Lists
- `GET /product-lists`
- `POST /product-lists`

### Credentials
- `GET /credentials/{network}/{user_id}`
- `PUT /credentials/{network}/{user_id}`
- `DELETE /credentials/{network}/{user_id}`

## Supabase

- Tabelas e RLS mantidos da migração existente
- A API usará `service_role` key se precisar bypassar RLS, ou `anon` se RLS cobrir as operações

## Segurança

- CORS restrito à origem do frontend
- Rate limiting (em avaliação)
- CSRF protection (em avaliação)
- Credenciais cifradas com Fernet (mantido da implementação anterior)
- RLS do Supabase mantido

## Deploy no Render

- Frontend React: Web Service (static ou Docker)
- API Python: outro Web Service (ou monorepo com ambos)
- Banco Supabase: externo (supabase project)

## Scripts

- `scripts/dev.sh` — inicia API + frontend em dev mode com reload
- `scripts/lint.sh` — lint da API e frontend
- `scripts/test.sh` — pytest + vitest
- `scripts/migrate.sh` — migrations do Supabase

## CI/CD

- `ci.yml` — pipeline de integração contínua: lint + test para API Python
- `cd.yml` — pipeline de entrega contínua: deploy no Render (se houver integração)

Para saber mais, consulte [.github/workflows/README.md](.github/workflows/README.md).

## Contato

## Contato

**Raffa Studio Produções**
E-mail: **contato.raffasp@gmail.com**

---

# Documentação Viva

Este README reflete o estado real do projeto. Uma funcionalidade só está completa quando:
- O código está no repositório
- Os docs (README, checklist, roadmap) estão atualizados
- O Vault J.A.R.V.I.S tem o documento correspondente

## Índice de documentos

### Processo
- [x] PRD — `00-Resumo-e-PRD.md` (Vault)

### Migração (em andamento)
- `docs/CHECKLIST_MIGRACAO.md` — checklist por módulo
- `docs/ROADMAP_MIGRACAO.md` — roadmap de migração
- `api/README.md` — documentação da nova API

### Infra
- Supabase: `15-Relatorio-Migracao-Supabase.md` (Vault)
- Deploy Render: `26-Deploy-Render.md` (Vault)

## Contato

**Raffa Studio Produções**
E-mail: **contato.raffasp@gmail.com**
