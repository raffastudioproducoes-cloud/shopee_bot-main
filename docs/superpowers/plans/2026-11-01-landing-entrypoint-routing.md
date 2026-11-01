# Landing Entrypoint Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar entrada inteligente na raiz, dashboard em /app e link público /presentation sem regressão de autenticação.

**Architecture:** Reusar TanStack Router e `authApi.me()` para validar cookie no servidor na entrada. Manter Flask SPA e Supabase OAuth intactos, com ajustes pontuais de navegação, alias legado e head Open Graph estático.

**Tech Stack:** React 19, TanStack Router, Zustand, TypeScript/Vite, Flask SPA, Node test runner, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-01-landing-entrypoint-routing-design.md`

## Global Constraints
- Branch de trabalho baseada em staging, sem merge à main ou alterações em ambientes de produção.
- Preservar visual e conteúdo da landing aprovada em `/apresentacao` (agora acessível em `/presentation`).
- Rotas públicas sem sessão, dashboard/ADMIN dependentes de autenticação real no backend e acessos USER/ADMIN existentes.
- Não mexer em Supabase, configuração OAuth externa, SMS/SMTP, banco, redes sociais ou dados reais.
- Preservar o mecanismo `isAdminVisitingSite` para acesso ADMIN ao dashboard do cliente.
- Não inventar integração/feature, nem alterar planos ou copy comercial.

## Review Focus
- LocalStorage indica login mas cookie está expirado: `/` deve abrir landing sem exibir painel.
- Callback Google cria cookie enquanto Zustand está deslogado: `/` deve confirmar `authApi.me` e redirecionar corretamente.
- Sessão ADMIN com flag de visita ao site: entrada e volta entre site e admin sem loop.
- Link `/presentation` para usuário autenticado: permanece público, sem redirect.
- Rotas profundas `/posts`, `/admin/...` e login de suporte: não devem quebrar.

---

### Task 1: Entrada inteligente e dashboard isolado

**Files:**
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/pages/PanelPage.tsx`
- Modify: `frontend/src/pages/LoginPage.tsx`
- Modify if relevant: `frontend/src/pages/AdminLayout.tsx`
- Test: `frontend/tests/landing-entry-routing.test.mjs` (novo)
- Update existing tests: `frontend/tests/admin-site-separation.test.mjs`, se a regex anterior pressupor dashboard em `/`.

**Interfaces:**
- Consumes: `authApi.me(): Promise<MeResponse>` e `isAdminVisitingSite()`.
- Produces: rota `/` landing com `beforeLoad` de sessão, `/app` dashboard no painel autenticado.

- [ ] Step 1: Criar teste falhando cobrindo `/` público, `/app` privado, redirecionamentos USER/ADMIN, ausência de redirecionamento baseado só no Zustand e links internos.
- [ ] Step 2: Executar `node --test frontend/tests/landing-entry-routing.test.mjs` e observar FAIL pelo comportamento ausente.
- [ ] Step 3: Alterar somente as rotas e links necessários, preservar `requireAdmin` e guard do PanelPage, sem ciclos de redirect.
- [ ] Step 4: Reexecutar Node tests pertinentes + `npm run build` no frontend e corrigir até PASS.
- [ ] Step 5: Commitar a mudança no branch isolado.

### Task 2: URL estável de compartilhamento e metadados

**Files:**
- Modify: `frontend/src/router.tsx` (alias legado), `frontend/index.html`, `frontend/public/robots.txt` quando pertinente.
- Modify as needed: `web/routes/spa.py` (somente se necessário para URL/OG por caminho; evitar SSR amplo).
- Test: `frontend/tests/landing-entry-routing.test.mjs` e/ou `tests/web/test_landing_metadata.py`.

**Interfaces:**
- Consumes: `PresentationPage` e SPA Flask existente.
- Produces: `/presentation` estável, `/apresentacao` compatível, OG preview apontando apresentação.

- [ ] Step 1: Escrever teste que falha para `/presentation`, alias antigo, HTML inicial com Open Graph e URL de preview coerente.
- [ ] Step 2: Rodar teste e observar FAIL pelo cenário novo.
- [ ] Step 3: Alterar router e metadados com URLs públicas HTTPS; garantir `/presentation` pública mesmo quando logado.
- [ ] Step 4: Rodar Node tests, backend smoke unitário pertinente e build; corrigir até PASS.
- [ ] Step 5: Commitar.

### Task 3: Integração e homologação em staging

**Files:**
- Modify: `docs/GUIA-MESTRE-IA.md` e `docs/TASK.md` (estado/contratos, sem substituir o planejamento Vault).
- Update Node tests if regressions are identified; no passwords/chaves em tests.

**Interfaces:**
- Depends: Tasks 1–2.
- Produces: evidência de rotas, compatibilidade, status de testes e PR de staging.

- [ ] Step 1: Rodar `node --test frontend/tests/landing-entry-routing.test.mjs`, testes relacionados e `npm run build`; reportar cada resultado real.
- [ ] Step 2: Abrir PR para `staging` (não `main`); confirmar status da CI (`api` e `frontend`).
- [ ] Step 3: Fazer merge em staging somente após CI verde e autorização prevista para homologação, verificar Render staging live e HTTP no `/` e `/presentation`; testes autenticados humanos seguem como pendência se não houver sessão de teste autorizada.
- [ ] Step 4: Atualizar Vault `34-Planejamento-Landing-Publica-Auto-Orbital.md`, `TASK.md` e índice com SHAs e decisões reais em branch de docs/PR próprio, reler conteúdo salvo e checar gatilho domínio/SMTP.
- [ ] Step 5: Solicitar a Rafa homologação da navegação, sem publicar em main.

**Observação de ambiente:** se o projeto não estiver disponível como checkout local, usar connector GitHub com branch isolado e CI como evidência; não fingir execução local de `node`/`npm`.