# Publicacao de Midia e Agendamento por Rede Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar composicao, armazenamento e publicacao por rede sem falhas em cascata, com agendamento imediato, datado e semanal claro.

**Architecture:** O backend calcula o plano final a partir de capacidades realmente entregues, enquanto o frontend apenas antecipa esse resultado. Midia temporaria fica em armazenamento duravel no escopo do perfil, a criacao em lote persiste somente os planos entregaveis e cada publicador recebe apenas a composicao confirmada.

**Tech Stack:** FastAPI, Postgres/Supabase, React 19, TanStack Query, APScheduler, armazenamento Supabase, pytest, Vite e Playwright.

**Spec:** `docs/superpowers/specs/2026-10-12-publicacao-midia-agendamento-design.md`

## Global Constraints

- Trabalhar somente em `staging`; nao alterar `VERSION` ate a ultima tarefa.
- Todas as consultas e mutacoes de midia exigem `user_id` e `profile_id`.
- Uma rede incompativel nao cancela redes entregaveis.
- Fallback textual exige texto valido e suporte real do publicador.
- Nenhum segredo, token, URL assinada ou resposta externa bruta pode entrar no cliente, teste ou log.
- Kwai permanece fora.
- Cada modo novo requer teste unitario, API e confirmacao humana visivel em staging antes de ser declarado pronto.

## Review Focus

- Perfil B nao pode usar nem apagar midia temporaria do perfil A da mesma conta.
- Uma midia incompatível nao pode converter texto longo invalido em `text_only`.
- Um publicador nao pode receber modo anunciado pela interface que ele ainda ignora.
- Um job com varios dias deve executar somente nos dias escolhidos e manter jobs legados.
- Limpar o modal nao pode apagar midia ja anexada a post confirmado.

### Task 1: Capacidades reais e planejador seguro

**Files:** `api/network_limits.py`, `api/media_composition.py`, `frontend/src/lib/networkLimits.ts`, `frontend/src/lib/mediaComposition.ts`, `tests/api/test_media_composition.py`.

- [ ] Escrever casos vermelhos para texto invalido com midia invalida, fallback textual valido e modo nao entregue.
- [ ] Separar `platform_modes` de `delivered_modes`; o planejador so devolve modo entregue.
- [ ] Repetir a matriz tipada no frontend e manter a mesma classificacao visual.
- [ ] Executar testes do planejador e limites; revisar diff; commit isolado.

### Task 2: Midia temporaria duravel e escopada

**Files:** criar `database/migrations/046_add_durable_media_drafts.sql`; modificar `api/routers/posts.py`, modulo de armazenamento existente e `tests/api/test_posts_media_drafts.py`.

- [ ] Escrever testes vermelhos de ownership, expiracao e limpeza sem vinculo.
- [ ] Adicionar chave de armazenamento, estado temporario e expiracao sem editar a migration 014 ou reutilizar o numero 045.
- [ ] Subir e baixar arquivos pelo armazenamento duravel, preservando validacao atual de tipo e tamanho.
- [ ] Expor upload e cancelamento de rascunho no escopo do perfil; nunca apagar ativo com `posts_medias`.
- [ ] Executar testes de API; revisar diff; commit isolado.

### Task 3: Preview e criacao parcial por lote

**Files:** `api/routers/posts.py`, `frontend/src/api/posts.ts`, `tests/api/test_posts_media_drafts.py`, `tests/api/test_posts_network_routing.py`.

- [ ] Escrever testes vermelhos de preview sem escrita, ordem de midia, `group_id` servidor e criacao parcial.
- [ ] Implementar preview que recalcula o plano com ativos pertencentes ao perfil.
- [ ] Implementar `POST /posts/batch`, vinculando somente midias aprovadas, criando jobs por rede e devolvendo modo/avisos/bloqueios sanitizados.
- [ ] Executar testes de posts, perfis e planejador; revisar diff; commit isolado.

### Task 4: Agendamento e estados confiaveis no compositor

**Files:** criar `database/migrations/047_add_scheduler_days_of_week.sql`; modificar `api/routers/posts.py`, `database/schedulers.py`, `scheduler/__init__.py`, `frontend/src/pages/PostsPage.tsx`, componentes de post e testes de scheduler/API.

- [ ] Escrever testes vermelhos para lista de dias, legado `day_of_week`, disparo imediato e valores locais iniciais.
- [ ] Preservar jobs legados e suportar um a sete dias nos novos jobs.
- [ ] Pré-carregar status real das credenciais do perfil; redes so ficam ativas depois de teste `ok`.
- [ ] Renomear os modos para `Publicar agora`, `Agendar` e `Agendar recorrencia`; inicializar data/hora nativas e adicionar limpeza segura do rascunho.
- [ ] Executar testes API/scheduler e build frontend; revisar diff; commit isolado.

### Task 5: Interface de preview, abas e fallback parcial

**Files:** criar `frontend/src/components/posts/MediaVariantTabs.tsx`; modificar `frontend/src/pages/PostsPage.tsx`, `frontend/src/components/posts/NetworkPicker.tsx`, `frontend/src/api/posts.ts`, testes de interface existentes ou novos testes de componentes.

- [ ] Implementar resumo por rede a partir do preview e abas somente quando a composicao divergir.
- [ ] Permitir confirmar quando houver ao menos uma rede entregavel; mostrar bloqueios vermelhos sem remover selecao silenciosamente.
- [ ] Implementar `Limpar postagem`, incluindo cancelamento de ativos temporarios ainda nao confirmados.
- [ ] Rodar build e verificacao visual desktop/mobile; revisar diff; commit isolado.

### Task 6: Publicadores por capacidade comprovada

**Files:** `scheduler/bot_post*.py`, `apis/facebook.py`, `apis/instagram.py`, `apis/x.py`, `apis/tiktok.py`, respectivos testes de scheduler/API.

- [ ] Manter Threads como referencia e faze-lo consumir midia duravel.
- [ ] Entregar Facebook e Instagram por modo, com teste por imagem unica, carrossel e video antes de anunciar cada um.
- [ ] Entregar upload de imagem X apenas com OAuth `media.write`; conexoes antigas devem pedir reconexao, sem fallback oculto.
- [ ] Entregar TikTok Photo Direct somente com Creator Info e URL verificada; manter bloqueado quando o requisito externo nao estiver pronto.
- [ ] Executar testes por publicador e registrar validacao humana de staging; cada modo recebe commit isolado.

### Task 7: Regressao, documentacao e versao final

**Files:** `docs/MEMORY.md`, `docs/TASK.md`, `docs/ARCHITECTURE.md`, `README.md`, `VERSION` e Vault/backup Drive correspondentes.

- [ ] Rodar suites API/scheduler, lint, build, diff check, audit e varredura de segredos.
- [ ] Fazer validacao humana em staging por modo/rede e registrar apenas resultados observados.
- [ ] Atualizar documentacao do projeto, Vault e backup Drive sem credenciais.
- [ ] Somente com todas as tarefas validadas, mudar `VERSION` de `2.1.0` para `2.2.0`, revisar tudo e fazer um unico push final para `staging`.

## Self-review

- O plano separa capacidade, armazenamento, lote, agendamento, interface e publicadores para que cada etapa tenha teste proprio.
- As migrations novas iniciam em 046 e 047; nenhuma migration historica e reescrita.
- A subida de versao aparece apenas na Task 7 e depende de validacao completa.
- Os cinco riscos de Review Focus pertencem respectivamente as Tasks 2, 1, 6, 4 e 5.
