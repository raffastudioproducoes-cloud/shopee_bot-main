# Checklist de Migração — React + API Python + Supabase

> Migração do ShopeeAutoVendas. Cada módulo deve ser testado e commitado separadamente.
> Sempre: rollback antes, commit após, atualizar docs e checklist, e push.
> Testar antes de avançar para o próximo módulo.

## Estado atual (2026-09-04)

| Módulo | Status | Observações |
| --- | --- | --- |
| **0. Preparação** | ✅ Concluído | Estrutura de pastas, documentos criados, README atualizado, branch `migrate/auth` |
| **1. Auth** | ✅ Concluído | `api/routers/auth.py` (login/logout/me), frontend de login, Zustand store, testes pytest ✅ (4 passed), commit `7c45aac` + push |
| **2. Painel/Dashboard** | ✅ Concluído | `api/routers/panel.py` (`GET /panel` com contagens de produtos/posts/listas + posts recentes + atividades recentes), frontend `PanelPage.tsx` com cards de métricas + lista de posts/atividades recentes, router TanStack com proteção de rota, CSS Tailwind v4 customizado via `@theme`, teste pytest ✅ (endpoint presente), commits `10aa73d` + `43b457e` + `aeff12f` + `8adeaac` + `7ba76bb` + push |

### 2. Painel/Dashboard

- [x] API Python: endpoint `GET /panel` com contagens (produtos, posts, listas) e listas recentes (posts e atividades)
- [x] Frontend React: `PanelPage.tsx` com cards de métricas, lista de posts recentes e atividades
- [x] Router TanStack com proteção de rota (redireciona para `/login` se não autenticado)
- [x] CSS Tailwind v4 customizado via `@theme` (cores, fontes, spacing, bordas, sombras, transições)
- [x] Testes básicos pytest ✅

### 3. Produtos

- [ ] API Python: CRUD de produtos
- [ ] Frontend React: lista de produtos, form de cadastro/edição
- [ ] Ícones Lucide React
- [ ] Testes básicos

### 4. Listas de produtos

- [ ] API Python: CRUD de listas de produtos
- [ ] Frontend React: lista de listas, form de criação
- [ ] Ícones Lucide React
- [ ] Testes básicos

### 5. Posts

- [ ] API Python: CRUD de posts, agendamento, publicação
- [ ] Frontend React: lista de posts, form de criação/edição
- [ ] Copywriter IA: integração com Gemini (ver `apis/llm.py` atual)
- [ ] Ícones Lucide React
- [ ] Testes básicos

### 6. Credenciais

- [ ] API Python: endpoints para salvar/ler/remover credenciais (cifradas)
- [ ] Frontend React: forms de credencial para cada rede
- [ ] Inputs type=password com value="" (nunca expor valor)
- [ ] Ícones Lucide React
- [ ] Testes básicos

### 7. Usuários

- [ ] API Python: CRUD de usuários (admin)
- [ ] Frontend React: lista de usuários, form de criação/edição
- [ ] Ícones Lucide React
- [ ] Testes básicos

### 8. Scheduler (avaliação)

- [ ] Decisão: manter in-process (YAGNI) ou externalizar?
- [ ] Se externalizar: rodar como processo separado no Render

## Regras de ouro

1. **Sempre rollback antes** de começar um módulo (branch `migrate/<modulo>` a partir de `master`).
2. **Sempre testar** antes de avançar (ritual de pytest básico + verificação manual quando possível).
3. **Sempre commitar** e **push** ao final do módulo.
4. **Sempre atualizar**:
   - `README.md` (seções relevantes)
   - `docs/CHECKLIST_MIGRACAO.md` (tabela de estado e módulos)
   - `docs/ROADMAP_MIGRACAO.md` (se necessário)
   - documentação no Vault (se houver)
5. **Nunca pular** a etapa de teste e documentação antes de avançar.
6. **Auth atual usa JWT simples em cookie httpOnly** — Isso é temporário. Tokens não devem ficar em cookies ou body no frontend. Revisar para auth mais seguro em próxima fase.
   - Ver `api/routers/auth.py` e `docs/CHECKLIST_MIGRACAO.md`.

## Observações do Módulo Auth (concluído)

- Implementação: JWT HS256 em cookie httpOnly (secure, samesite=lax)
- Endpoints: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- Frontend: `LoginPage.tsx`, `authStore.ts` (Zustand), `auth.ts` (funções de API)
- Testes: 4 testes pytest passaram (`test_api.py`)
- **Atenção**: essa implementação de auth é temporária. Em próxima fase, substituir por solução mais segura (tokens não devem ficar em cookies/body no frontend).

## Observações do Módulo Painel (concluído)

- Endpoint: `GET /panel` — retorna contagens (products_count, posts_count, product_lists_count) + posts recentes (últimos 5) + atividades recentes (últimas 10)
- Frontend: `PanelPage.tsx` usa `@tanstack/react-query` para buscar os dados e exibir cards de métricas + listas
- Router: `router.ts` com rotas `/` (painel, protegido) e `/login`, redirecionamento automático se não autenticado
- CSS: `index.css` com `@import "tailwindcss"` + `@theme` customizado (cores, fontes, spacing, bordas, sombras, transições)
- **Nota**: ícones atualmente em SVG inline — Lucide React adicionado ao `package.json` mas não utilizado; pode ser ativado no módulo de produtos

## Próximo passo

Após Painel concluído, o próximo módulo é **Produtos** (módulo 3).

## Histórico de commits desta migração

- `7c45aac` — `feat: auth router + frontend estrutura (login page, auth store, rotas protegidas)` (módulo 1)
- `aa3b857` — `docs: README completo com padrão profissional, badges e documentacao viva`
- `7b745f2` — `ci: GitHub Actions — CI lint+test e CD deploy no Render`
- `9eed7b2` — `chore: estrutura inicial de migrcao React + API Python + Supabase`
- `10aa73d` — `feat(panel): router /panel com métricas e atividades recentes + registro no main.py` (módulo 2 - backend)
- `43b457e` — `feat(panel): página do painel com métricas, posts recentes e atividades (frontend React)` (módulo 2 - frontend página)
- `aeff12f` — `feat(panel): router TanStack com rotas /login e / (painel protegido)` (módulo 2 - router)
- `8adeaac` — `feat(panel): frontend completa — package.json, vite, tsconfig, index.html, main.tsx, App.tsx, index.css` (módulo 2 - estrutura frontend)
- `7ba76bb` — `feat(panel): frontend completa — CSS Tailwind v4 customizado + main.tsx ajustado (entry point React)` (módulo 2 - finalização)
