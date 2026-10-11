# Conta, Perfis e Papéis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar Shopee, IA e produtos compartilhados por conta, mantendo a operação social isolada por perfil e carregando recursos administrativos somente para ADMIN.

**Architecture:** O banco conserva `profile_id` legado apenas como histórico onde necessário, mas os recursos compartilhados passam a ser resolvidos por `user_id`; listas referenciam produtos da mesma conta e continuam por perfil. O frontend separa perfis comuns dos módulos de gestão administrativa, que são importados dinamicamente após o papel ser confirmado pelo servidor. O backend é a única autoridade para acesso ADMIN.

**Tech Stack:** PostgreSQL/Supabase migrations, FastAPI, Python, React 19, TypeScript, TanStack Router, Zustand, pytest, Vite.

**Spec:** `docs/superpowers/specs/2026-10-11-conta-perfis-papeis-design.md`

## Global Constraints

- Usuário tem exatamente um perfil principal e no máximo dois adicionais.
- Shopee, IA e produtos pertencem a `user_id`, nunca a um perfil.
- Redes sociais, testes, listas, posts, mídia, agendamentos, resultados, notificações e preferências pertencem a `user_id` + `profile_id`.
- Nenhuma ação administrativa é autorizada pelo frontend; todo endpoint ADMIN verifica a sessão no backend.
- USER não recebe texto, rota navegável ou módulo que revele administração técnica.
- Alterações de schema são aditivas, transacionais e falham fechadas diante de conflito de dados; não registrar segredos.
- Commits e push somente em `staging`; nenhuma promoção para `main` sem autorização posterior do Rafa.

## Review Focus

- Dois perfis com produto Shopee duplicado antigo: a migração deve abortar sem escolher valor ou segredo.
- Lista do perfil A tentando referenciar produto de outra conta: deve ser rejeitada.
- JOB sem `profile_id`: deve falhar fechado; produto compartilhado não relaxa esse requisito.
- USER manipulando URL, DOM ou localStorage: não recebe módulo nem resposta administrativa.
- Mudança de `ADMIN` para `USER` no servidor: próxima revalidação deve remover módulos administrativos sem depender do estado persistido.

---

### Task 1: Migração segura de posse compartilhada

**Files:**
- Create: `database/migrations/045_share_account_catalog_credentials.sql`
- Modify: `database/migrations/041_products_unique_per_profile.sql` (somente referência/documentação histórica se necessária)
- Test: `tests/database/test_045_share_account_catalog_credentials.py`

**Interfaces:**
- Consumes: linhas legadas de `products`, `shopee_credentials` e `ai_credentials` com `user_id` e `profile_id`.
- Produces: uma única identidade por conta para produto (`user_id`, `product_id`), Shopee e IA (`user_id`, provider), com `profile_id` nulo nesses recursos.

- [ ] **Step 1: Escrever testes de migração para consolidação e conflito**
  Cobrir uma linha legada por recurso e duas linhas divergentes da mesma conta; a segunda deve abortar antes de alterar dados.
- [ ] **Step 2: Confirmar falha dos testes antes da migração**
  Run: `pytest tests/database/test_045_share_account_catalog_credentials.py -q`
  Expected: FAIL porque a migração ainda não existe.
- [ ] **Step 3: Implementar migração transacional `045`**
  Detectar duplicatas incompatíveis por conta e lançar erro explícito; somente sem conflito, normalizar `profile_id` para `NULL`, recriar índices únicos por conta e índices de consulta por `user_id`.
- [ ] **Step 4: Validar migração e reversibilidade operacional**
  Run: `pytest tests/database/test_045_share_account_catalog_credentials.py -q`
  Expected: PASS sem duplicação silenciosa ou perda de segredo.
- [ ] **Step 5: Commit**
  `git commit -m "feat: compartilha catalogo e credenciais por conta"`

### Task 2: Serviços e rotas de recursos compartilhados

**Files:**
- Modify: `api/routers/products.py`, `api/routers/catalog.py`, `api/routers/credentials.py`
- Modify: `api/ai_credentials.py`, `database/products.py`, `database/shopee_credentials.py`
- Test: `tests/api/test_products.py`, `tests/api/test_ai_credentials.py`, `tests/api/test_credentials.py`, `tests/api/test_catalog.py`

**Interfaces:**
- Consumes: `user_id` autenticado e `profile_id` ativo quando a rota também cria recurso isolado.
- Produces: produtos, Shopee e IA lidos/escritos só por `user_id`; OAuth social permanece por `user_id` + `profile_id`.

- [ ] **Step 1: Escrever casos de conta compartilhada**
  Criar recursos no perfil A e ler/usar no perfil B da mesma conta; provar 404 para outra conta e preservar 403 de overrides sociais a USER.
- [ ] **Step 2: Confirmar falha contra o escopo atual por perfil**
  Run: `pytest tests/api/test_products.py tests/api/test_ai_credentials.py tests/api/test_credentials.py tests/api/test_catalog.py -q`
  Expected: FAIL nos casos de perfil B.
- [ ] **Step 3: Criar helper explícito de escopo de conta e migrar chamadores**
  Usar o helper somente para produtos, Shopee e IA. Não alterar `scope_owner` de dados sociais.
- [ ] **Step 4: Validar rotas compartilhadas e sociais isoladas**
  Run: comandos da etapa 2 mais `pytest tests/api/test_profile_scope_credentials.py -q`
  Expected: PASS; token social do perfil A continua invisível no perfil B.
- [ ] **Step 5: Commit**
  `git commit -m "feat: resolve catalogo e chaves por conta"`

### Task 3: Listas e posts com catálogo compartilhado

**Files:**
- Modify: `api/routers/lists.py`, `api/routers/posts.py`, `scheduler/update_products.py`
- Modify: backup/restore sob `api/routers/profiles.py` e serviços associados
- Test: `tests/api/test_lists.py`, `tests/api/test_posts_network_routing.py`, `tests/api/test_profile_scope_posts.py`, testes de backup existentes

**Interfaces:**
- Consumes: lista/post do perfil ativo e IDs de produtos da mesma conta.
- Produces: listas, posts e jobs permanecem por perfil, podendo apontar para produto compartilhado do mesmo usuário.

- [ ] **Step 1: Escrever testes de associação cruzada válida e inválida**
  Perfil B pode inserir produto da conta em sua lista; outra conta recebe 400/404; posts e jobs preservam `profile_id` obrigatório.
- [ ] **Step 2: Confirmar falha no validador atual por perfil**
  Run: `pytest tests/api/test_lists.py tests/api/test_profile_scope_posts.py -q`
  Expected: FAIL na lista do perfil B com produto compartilhado.
- [ ] **Step 3: Ajustar validações e backup/restauração**
  Validar produto por conta, não por perfil; manter ownership da lista/post/mídia e nunca copiar conteúdo isolado para outro perfil.
- [ ] **Step 4: Validar fluxo completo**
  Run: testes da etapa 1, testes de scheduler de perfil e backup/restauração.
  Expected: PASS; troca de perfil não move listas, posts ou agendas.
- [ ] **Step 5: Commit**
  `git commit -m "feat: usa catalogo compartilhado em listas e posts"`

### Task 4: Perfis comuns e módulos administrativos separados

**Files:**
- Create: `frontend/src/pages/UsersPage.tsx`
- Modify: `frontend/src/pages/ProfilesPage.tsx`, `frontend/src/pages/PanelPage.tsx`, `frontend/src/router.tsx`, `frontend/src/stores/authStore.ts`
- Test: `frontend/src/router.test.tsx` or existing frontend test location

**Interfaces:**
- Consumes: papel revalidado por `authApi.me()` e perfil ativo do usuário.
- Produces: `/profiles` para todos; `/users` e `/logs` somente ADMIN, importados dinamicamente após guard de rota.

- [ ] **Step 1: Escrever testes de navegação e carga por papel**
  USER vê Perfis, não vê Users/Logs e é redirecionado silenciosamente ao tentar URL administrativa; ADMIN vê todos os itens.
- [ ] **Step 2: Confirmar falha com rota e página acopladas atuais**
  Run: teste frontend correspondente.
  Expected: FAIL porque `/profiles` contém gestão de usuários e imports são estáticos.
- [ ] **Step 3: Extrair gestão de usuários para `UsersPage` e aplicar lazy imports**
  Revalidar `authApi.me()` no bootstrap; routes ADMIN usam guard antes da importação do chunk. Remover qualquer mensagem de negação administrativa da UI USER.
- [ ] **Step 4: Validar bundle e comportamento de rota**
  Run: `npm run build` e testes frontend.
  Expected: chunks administrativos separados; USER não recebe UI ou pista administrativa.
- [ ] **Step 5: Commit**
  `git commit -m "feat: separa perfis comuns de modulos admin"`

### Task 5: Credenciais comuns sem código administrativo carregado

**Files:**
- Create: `frontend/src/components/credentials/AdminOverrides.tsx`
- Modify: `frontend/src/pages/CredentialsPage.tsx`, `frontend/src/api/credentials.ts`
- Test: testes frontend de credenciais e `tests/api/test_credentials.py`

**Interfaces:**
- Consumes: sessão ADMIN validada e status por perfil.
- Produces: tela comum com Shopee, IA e OAuth; painel técnico lazy ADMIN para overrides sociais.

- [ ] **Step 1: Escrever testes de ausência de controles administrativos para USER**
  Cobrir token manual, portal de desenvolvedor, diagnóstico e chamada de API inexistentes na árvore USER.
- [ ] **Step 2: Confirmar falha no componente atual**
  Run: teste frontend de credenciais.
  Expected: FAIL porque o arquivo atual contém ambos os fluxos.
- [ ] **Step 3: Extrair overrides para chunk ADMIN**
  Manter OAuth e status no componente comum; só importar o painel técnico após papel confirmado. Backend continua exigindo ADMIN.
- [ ] **Step 4: Validar UI e proteção de API**
  Run: testes frontend, `pytest tests/api/test_credentials.py -q`, `npm run build`.
  Expected: PASS; request manual de USER retorna 403 e não há pista visual.
- [ ] **Step 5: Commit**
  `git commit -m "feat: isola overrides sociais de administrador"`

### Task 6: Regressão, documentação e validação de staging

**Files:**
- Modify: `docs/ARCHITECTURE.md`, `docs/PRD.md`, `docs/TASK.md`, `docs/MEMORY.md`
- Modify: Vault `Projetos/ShopeeAutoVendas/00-INDICE-Estado-Atual.md` and contract document
- Test: suites API, scheduler and frontend build

**Interfaces:**
- Consumes: entregas das Tasks 1-5.
- Produces: contrato atualizado, backup Drive conferido e evidência de staging sem segredos.

- [ ] **Step 1: Rodar regressão completa e auditoria de diff**
  Run: `pytest tests/api --confcutdir=tests/api -q`, suites scheduler pertinentes, `npm run build`, `git diff --check`.
  Expected: PASS sem regressão de isolamento social.
- [ ] **Step 2: Atualizar documentação e Vault sem valores sensíveis**
  Registrar matriz conta/perfil/papel, migração aplicada, limites e evidências. Copiar documentos ao backup Drive e verificar hashes.
- [ ] **Step 3: Validar manualmente em staging**
  USER cria/alternar perfil e usa catálogo comum; ADMIN usa Users/Logs/override; tentativa direta USER continua bloqueada.
- [ ] **Step 4: Commit e push em staging**
  `git commit -m "docs: registra migracao de conta e perfis"`
  `git push origin staging`
  Não criar merge para `main` nesta tarefa.

## Self-review do plano

- Cobertura do spec: Tasks 1-3 cobrem dados compartilhados e isolamento; Tasks 4-5 cobrem papéis, carregamento e ausência de pistas; Task 6 cobre regressão, documentação e staging.
- Consistência: `user_id` é o escopo de conta; `user_id` + `profile_id` é o escopo operacional; apenas os três recursos definidos usam escopo de conta.
- Riscos do Review Focus: conflito de migração está na Task 1; associação de lista e jobs nas Tasks 3; tentativa de USER e mudança de papel nas Tasks 4-5.
- Proporção: seis entregas testáveis e reversíveis; nenhuma promove código para `main`.
