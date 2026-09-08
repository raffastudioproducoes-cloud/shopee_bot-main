# Checklist de Migração — React + API Python + Supabase

> Migração do ShopeeAutoVendas. Cada módulo deve ser testado e commitado separadamente.
> Sempre: rollback antes, commit após, atualizar docs e checklist, e push.
> Testar antes de avançar para o próximo módulo.

## Estado atual (2026-09-04)

| Módulo | Status | Observações |
| --- | --- | --- |
| **0. Preparação** | ✅ Concluído | Estrutura de pastas, documentos criados, README atualizado, branch `migrate/auth` |
| **1. Auth** | ✅ Concluído | `api/routers/auth.py` (login/logout/me), frontend de login, Zustand store, testes pytest ✅ (4 passed), commit `7c45aac` + push |

## Módulos por fazer

### 2. Painel/Dashboard

- [ ] API Python: endpoints para contagens (produtos, posts, listas, atividades)
- [ ] Frontend React: dashboard com cards, atividade recente
- [ ] Ícones Lucide React
- [ ] Testes básicos

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

## Próximo passo

Após Auth concluído, o próximo módulo é **Painel/Dashboard** (módulo 2).

## Histórico de commits desta migração

- `7c45aac` — `feat: auth router + frontend estrutura (login page, auth store, rotas protegidas)` (módulo 1)
- `aa3b857` — `docs: README completo com padrão profissional, badges e documentacao viva`
- `7b745f2` — `ci: GitHub Actions — CI lint+test e CD deploy no Render`
- `9eed7b2` — `chore: estrutura inicial de migrcao React + API Python + Supabase`
