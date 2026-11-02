# Auto Orbital — Campanhas por lista Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disponibilizar criação de posts em página dedicada, múltiplas fotos Shopee e publicação sequencial de campanhas de listas, com segurança de agendamento e histórico por ocorrência.

**Architecture:** Reutilizar a infraestrutura atual de posts, mídias, composição por rede, fila de publicação e Supabase cron. Separar editor de campanha, snapshot de itens e slots idempotentes; preservar legado e executar publicações por autoridade central sem concorrência entre staging e produção.

**Tech Stack:** React 19, TypeScript 5.6, TanStack Router/Query, FastAPI, Flask bridge/APScheduler, Supabase PostgreSQL + Storage privado, pytest e node:test.

**Spec:** [2026-11-02-campanhas-listas-design.md](../specs/2026-11-02-campanhas-listas-design.md)

## Global Constraints

- Requisitos `R01` a `R18` são obrigatórios conforme a especificação.
- `VERSION` é a fonte oficial; baseline `3.0.0`. Em staging registrar mudanças em `CHANGELOG.md [Não lançado]`; SemVer PATCH só para bugs, MINOR para recursos.
- `staging` é exclusivo do desenvolvedor, mas banco Supabase compartilhado e execução central na produção; não criar cron duplicado.
- Período máximo da campanha = 30 dias inclusivos, contado em calendário de `America/Sao_Paulo`; não ativar entitlements comerciais nesta entrega.
- Falhas não interrompem a sequência. Só editar futuras ocorrências não reivindicadas.
- Não publicar externamente sem conta/destino autorizados. Não migrar destrutivamente nem alterar dados/tokens existentes.
- TikTok Photo e tags/cotas por plano ficam em **backlog rastreável de alta prioridade**; nunca anunciar como disponíveis.

## Review Focus

1. Duas agendas criadas em ambientes distintos no mesmo segundo: **um único** claim/execução por ocorrência, sem perder agendas de staging.
2. Virada de mês/ano e período inclusivo 30/31 dias: contador correto em Brasília, sem slot duplicado.
3. Post com conteúdo compartilhado entre redes e falha numa: não gerar duplicação de sucesso parcial ou retry de `unknown`.
4. Mudança de item, ordem ou mídia em campanha já ativa: nenhuma alteração retroativa e nenhuma mutação de ocorrência iniciada.
5. Galeria remota de mídia com MIME falso, host incorreto, redirect ou arquivo grande: rejeição segura, sem download arbitrário e sem vazamento de bucket.

---

## Mapa de arquivos (proposta inicial)

**Existentes a preservar/refatorar:**
- `frontend/src/pages/PostsPage.tsx` — retirar o compositor; manter listagem/modal detalhes.
- `frontend/src/pages/PanelPage.tsx`, `frontend/src/router.tsx` — navegação e rotas.
- `frontend/src/components/posts/*` — componentes reutilizáveis de editor, preview, seleção, mídias.
- `frontend/src/lib/networkLimits.ts`, `mediaAdapt.ts`, `mediaComposition.ts` — limites atuais; só evoluir com testes.
- `api/routers/posts.py`, `api/network_limits.py`, `api/media_composition.py`, `api/internal_client.py`, `web/routes/internal.py`, `database/schedulers.py`, `database/publish_jobs.py` — contrato de postagem, execução e mídia.
- `apis/shopee.py`, `api/shopee_catalog.py`, `api/routers/catalog.py`, `api/routers/products.py` — origem/catalogação de imagens.
- `CHANGELOG.md`, `VERSION`, `docs/ARCHITECTURE.md`, `docs/TASK.md` — documentação por fase.

**Novos módulos focados, a confirmar após inspeção final:**
- `frontend/src/pages/CreatePostPage.tsx` e `frontend/src/components/posts/PostComposer.tsx` — UI em página, modalidades.
- `frontend/src/components/campaigns/{CampaignEditor,CampaignItemEditor,CampaignSchedule,CampaignPreview}.tsx` — campanha.
- `frontend/src/api/campaigns.ts`; `frontend/src/lib/campaignSchedule.ts` — contrato API/previsão.
- `api/routers/campaigns.py`, `api/campaign_schedule.py`, `api/campaign_dispatch.py` — CRUD, calendário puro e integração de execução.
- `database/migrations/068_*.sql` ou próximo número livre, somente aditivas; `tests/api/test_campaigns.py`, `tests/api/test_campaign_schedule.py`, `tests/scheduler/test_campaign_dispatch.py`, `frontend/tests/campaigns.test.mjs`.
- `docs/POSTS-CAMPANHAS-RESULTADOS-20261102.md` — evidências de execução e QA incremental.

## F0 — Segurança e compatibilidade de agendamento (`3.0.1`, se bug reproduzido)

### Task 1 — Auditoria executável do agendador compartilhado

**Files:** Test `tests/scheduler/test_dual_environment.py`; inspect `docs/SCHEDULER-ENVIRONMENTS-20261102.md`, `database/scheduler_environment.py`, `api/internal_client.py`, `web/routes/internal.py`.

**Interfaces:** Produces: contrato de criação e claim `staging` → executor central de produção, preservando `user_id/profile_id/post_id`. Consumes: scheduler e jobstore atuais.

- [ ] **Step 1: Escrever teste que reproduz** uma agenda criada por staging que produção não enxerga, além de teste com dois workers concorrendo pelo mesmo slot.
- [ ] **Step 2: Rodar `pytest tests/scheduler/test_dual_environment.py -q`** e confirmar falha específica esperada.
- [ ] **Step 3: Documentar diagnóstico** com origem exata, efeitos sobre agendas antigas e plano de migração sem riscos; não corrigir por especulação.
- [ ] **Step 4: Comprovar condição** contra dados/configurações somente por consultas read-only e auditoria sem postagem externa.

### Task 2 — Convergência segura em executor único

**Files:** Modify `database/scheduler_environment.py`, `database/schedulers.py`, `database/publish_jobs.py`, `api/internal_client.py`, `web/routes/internal.py`, teste da Task 1, migration aditiva se estritamente necessário.

**Interfaces:** Produces: criação de agenda em ambos os sites e claim de apenas um executor responsável; atualização de agenda com scope de usuário/perfil; `publish_jobs` existente mantém idempotência. Consumes: contrato Task 1.

- [ ] **Step 1: Criar testes RED** para staging → produção, legado não deslocado e dois executores sem duplicação.
- [ ] **Step 2: Implementar a menor correção compatível** respeitando tabela/jogos de scheduler e o Supabase cron central; se houver mudança de configuração Render, fazer rollout por etapas com main já compatível.
- [ ] **Step 3: Rodar testes verdes**: `pytest tests/scheduler/test_dual_environment.py tests/scheduler/test_publish_jobs.py tests/api/test_recurring_scheduler_bridge.py -q`.
- [ ] **Step 4: Atualizar `CHANGELOG.md [Não lançado]` e documentação**, com migração/auditoria/limites efetivamente vistos.
- [ ] **Step 5: Commit de correção**, PR para staging, CI; não promover à main sem aprovação. Marcar `3.0.1` apenas na promoção aprovada, se este for o único escopo de patch.

## F1 — Criar POST como página (`3.1.0` MINOR)

### Task 3 — Extrair compositor atual preservando comportamento

**Files:** Create `frontend/src/components/posts/PostComposer.tsx`, `frontend/src/pages/CreatePostPage.tsx`; modify `frontend/src/pages/PostsPage.tsx`; test `frontend/tests/posts-composer.test.mjs`, `frontend/tests/form-drafts.test.mjs`.

**Interfaces:** Produces: `PostComposer` aceita `post?: Post` e callbacks de criação/edição; `CreatePostPage` cuida de navegação e modo. Consumes: `PostProductPicker`, `PostTimePicker`, `PostLivePreview`, `postsApi`, autosave atuais.

- [ ] **Step 1: Criar testes RED** que exigem /posts sem `Novo post`, compositor fora do modal, edição com `post.id` preservado e estados antigos mantidos.
- [ ] **Step 2: Ver falha** com `node --test frontend/tests/posts-composer.test.mjs frontend/tests/form-drafts.test.mjs`.
- [ ] **Step 3: Extrair sem refatoração funcional desnecessária** e evitar duplicar lógica em dois componentes.
- [ ] **Step 4: Rodar testes verdes**, build `cd frontend && npm run build`; verificar rascunhos, Android e acessibilidade de teclado.
- [ ] **Step 5: Commit + changelog**, sem marcar release antecipada.

### Task 4 — Navegação, preview e edição em página

**Files:** Modify `frontend/src/router.tsx`, `frontend/src/pages/PanelPage.tsx`, `frontend/src/components/posts/PostDetailsModal.tsx`; test `frontend/tests/posts-composer.test.mjs`.

**Interfaces:** Produces: `/posts/criar`, edição por URL `/posts/$postId/editar`, item menu `Criar POST` acima de `Automação`. Consumes: Task 3.

- [ ] **Step 1: Criar testes RED** de ordem/menu, rota protegida, retorno e abertura do detalhe.
- [ ] **Step 2: Rodar teste e verificar falha**, depois implementar roteamento e link de edição.
- [ ] **Step 3: Verificar** `node --test frontend/tests/posts-composer.test.mjs` e `cd frontend && npm run build`.
- [ ] **Step 4: Revisar visual desktop/Android** na identidade existente sem adicionar modal de criação novamente; documentar.

## F2 — Galeria Shopee e mídias (`3.1.0` MINOR)

### Task 5 — Fonte autorizada e modelo de múltiplas imagens

**Files:** Inspect `apis/shopee.py`, `api/shopee_catalog.py`, `api/routers/catalog.py`, `api/routers/products.py`; create migration aditiva para galeria se fonte validada; test `tests/api/test_catalog_search.py`, `tests/api/test_posts_media_drafts.py`.

**Interfaces:** Produces: lista ordenada de URLs/metadados de imagem por produto da conta e compatibilidade de `products.image`. Consumes: catálogo e validação atual.

- [ ] **Step 1: Fazer verificação oficial da capacidade da API Shopee** (campos de fotos adicionais, licitude, formato e autenticação), registrar evidências/limites no documento.
- [ ] **Step 2: Escrever teste RED** para múltiplas fotos de um produto sem perder o campo antigo, com ownership e separação de perfil.
- [ ] **Step 3: Criar armazenamento aditivo** e API de galeria; sem scraping ou endpoints privados não autorizados.
- [ ] **Step 4: Rodar** `pytest tests/api/test_catalog_search.py tests/api/test_posts_media_drafts.py -q`.
- [ ] **Step 5: Se a fonte não oferecer várias fotos, registrar bloqueio específico** e seguir com a importação manual segura enquanto a aquisição automática continua pendente, sem anunciar funcionalidade completa.

### Task 6 — Mídias múltiplas no compositor e adaptação por rede

**Files:** Modify `frontend/src/components/posts/{MediaTray,PostComposer}.tsx`, `frontend/src/lib/{mediaAdapt,networkLimits}.ts`, `api/routers/posts.py`, `api/network_limits.py`, `api/media_composition.py`; tests `frontend/tests/media-adapt.test.mjs`, `tests/api/test_media_composition.py`.

**Interfaces:** Produces: seleção/reordenação/capa de N fotos e resposta de adaptação por rede com aviso exato. Consumes: galeria Task 5 e mídias temporárias existentes.

- [ ] **Step 1: Testes RED** para 1/2/N fotos, MIME/host/redirect/limite de tamanho, opção `texto apenas` e rede bloqueada.
- [ ] **Step 2: Rodar testes e observar falha**; implementar normalização/upload para Storage privado e escolha de fotos.
- [ ] **Step 3: Verificar** `node --test frontend/tests/media-adapt.test.mjs frontend/tests/media-tray.test.mjs` e `pytest tests/api/test_media_composition.py tests/api/test_posts_media_drafts.py -q`.
- [ ] **Step 4: Aplicar mesmo componente à publicação única** e preparar reuso no editor de campanha; documentar e commitar.

## F3 — Editor e persistência da campanha (`3.2.0` MINOR)

### Task 7 — Schema aditivo, ownership e snapshot

**Files:** Create `database/migrations/069_*campaign*.sql (ou próximo número livre após 068)` (substituir pelo próximo número livre), `api/routers/campaigns.py`, `tests/api/test_campaigns.py`; modify `api/main.py`.

**Interfaces:** Produces `CampaignCreate`, `CampaignItemUpdate`, `CampaignDetail`, `POST /campaigns`, `GET /campaigns/{id}`, `PATCH /campaigns/{id}`, `PATCH /campaigns/{id}/items/{item_id}`; dados com owner `user_id/profile_id`, ordem e revision. Consumes: listas existentes e mídias Task 6.

- [ ] **Step 1: Teste RED** do snapshot da lista, ownership, exclusão/ordenação e edição de itens.
- [ ] **Step 2: Rodar `pytest tests/api/test_campaigns.py -q` e confirmar falha**.
- [ ] **Step 3: Criar migration somente aditiva**, índices/unique/RLS/constraints, API transacional e validação de produtos; manter tabelas legadas.
- [ ] **Step 4: Rodar testes verdes** e revisar índices/escopo account/profile.
- [ ] **Step 5: Commit + changelog + doc**.

### Task 8 — UI de preparação por produto e rascunho

**Files:** Create `frontend/src/api/campaigns.ts`, `frontend/src/components/campaigns/{CampaignEditor,CampaignItemEditor}.tsx`; modify `frontend/src/pages/CreatePostPage.tsx`; test `frontend/tests/campaigns.test.mjs`.

**Interfaces:** Produces: editor ordenável, alterações independentes de texto/link/mídias/capa por item, recuperação de rascunho, versões IA por rede. Consumes: APIs Task 7.

- [ ] **Step 1: Testes RED** de ordem, snapshot, restauração de campos vazios e edição de produto específico.
- [ ] **Step 2: Rodar** `node --test frontend/tests/campaigns.test.mjs` com falha esperada.
- [ ] **Step 3: Implementar editor responsivo** reusando composição, mídia e IA sem segundo motor de validação.
- [ ] **Step 4: Verificar testes, TypeScript/build**; documentar e commitar.

## F4 — Calendário e restrições oficiais (`3.2.0` MINOR)

### Task 9 — Planejador puro da grade e rotação

**Files:** Create `api/campaign_schedule.py`, `frontend/src/lib/campaignSchedule.ts` (somente preview ou espelho), `tests/api/test_campaign_schedule.py`, `frontend/tests/campaigns.test.mjs`.

**Interfaces:** Produces: `plan_campaign_slots(start_date, end_date, weekdays, start_time, end_time, interval_minutes, item_ids, timezone="America/Sao_Paulo") -> list[Slot]`; cada `Slot` tem sequência, horário UTC/local, item_id/posição. Backend autoritativo.

- [ ] **Step 1: Testes RED**: limites 30/31 dias inclusivos, horários 09/12/15/18, rotatividade 5→10, insuficiência 10→5, virada de mês e dias sem coincidência.
- [ ] **Step 2: Rodar `pytest tests/api/test_campaign_schedule.py -q` e confirmar falhas funcionais**.
- [ ] **Step 3: Implementar cálculo determinístico com `zoneinfo`** e erros claros para janela inválida.
- [ ] **Step 4: Validar paridade da prévia UI/backend**, sem permitir ativação com cobertura insuficiente silenciosamente; testes verdes e commit.

### Task 10 — Políticas de ritmo e prévia de ativação

**Files:** Create `api/campaign_rate_policy.py` ou módulo equivalente; modify `api/routers/campaigns.py`; test `tests/api/test_campaign_schedule.py` e `tests/api/test_campaigns.py`.

**Interfaces:** Produces: `validate_campaign_pacing(networks, slots, account_id, profile_id) -> PacingResult` com erros, alertas, intervalos mínimos e data da documentação consultada. Consumes: Task 9 e limites do publicador.

- [ ] **Step 1: Levantar fontes oficiais de políticas/rate limits** por rede e descrever o que não é verificável; não inventar valores nem prometer anti-ban garantido.
- [ ] **Step 2: Testes RED** para intervalo inválido, violação de cota de janela/24h, rede indisponível e 429.
- [ ] **Step 3: Implementar rejeição/ajuste explícito com prévia**: nenhuma alteração de hora fora da janela sem consentimento.
- [ ] **Step 4: Rodar testes verdes**; registrar políticas versionadas e commit.

### Task 11 — Configuração de calendário em tela

**Files:** Create `frontend/src/components/campaigns/{CampaignSchedule,CampaignPreview}.tsx`; modify `frontend/src/api/campaigns.ts`, `frontend/src/pages/CreatePostPage.tsx`; test `frontend/tests/campaigns.test.mjs`.

**Interfaces:** Produces: inputs de datas/dias/horas/intervalo/redes, preview por produto, ciclo, cobertura e alertas. Consumes: Tasks 9–10.

- [ ] **Step 1: Testes RED** para erros de 31 dias, zero slots, 10×5 e intervalo proibido, inclusive Android/foco.
- [ ] **Step 2: Rodar teste e observar falha**; construir interface sem modal de data/hora desktop antigo.
- [ ] **Step 3: Validar UX e backend autoritativo**, run `node --test frontend/tests/campaigns.test.mjs` e `cd frontend && npm run build`.
- [ ] **Step 4: Documentar e commitar**.

## F5 — Ativação, execução e observabilidade (`3.2.0` MINOR)

### Task 12 — Ocorrências e ativação idempotente

**Files:** Add migration somente aditiva, modify `api/routers/campaigns.py`; test `tests/api/test_campaigns.py`, `tests/scheduler/test_campaign_dispatch.py`.

**Interfaces:** Produces: `POST /campaigns/{id}/activate`, `POST /campaigns/{id}/pause`, `POST /campaigns/{id}/resume`, `POST /campaigns/{id}/cancel`, registros únicos por `campaign_id + sequence`, controles de revision; nunca apaga histórico.

- [ ] **Step 1: Testes RED** para ativação concorrente, PAUSED, duplicação de clique e update sobre ocorrência reivindicada.
- [ ] **Step 2: Rodar os testes e observar falha**; implementar transações/constraints/RLS.
- [ ] **Step 3: Rodar testes verdes** e commitar com documentação.

### Task 13 — Consumo central e materialização de posts individuais

**Files:** Create `api/campaign_dispatch.py` (ou módulo de scheduler equivalente); modify worker de produção e integração `publish_jobs`; tests `tests/scheduler/test_campaign_dispatch.py`, `tests/scheduler/test_publish_jobs.py`, `tests/scheduler/test_publication_claims.py`.

**Interfaces:** Produces: claim atômico da ocorrência, criação única de post `#ID` para cada rede compatível, ligação ao ledger, avanço de sequência independente de falha. Consumes: Tasks 2, 7, 9, 10, 12.

- [ ] **Step 1: Testes RED** para mesma hora/múltiplos usuários, duplicação de worker, postagem parcial por rede, erro 403, `unknown`, reinício no meio.
- [ ] **Step 2: Rodar testes e verificar falha**; implementar processamento transacional e idempotência com `posts` existentes.
- [ ] **Step 3: Rodar** `pytest tests/scheduler/test_campaign_dispatch.py tests/scheduler/test_publish_jobs.py tests/scheduler/test_publication_claims.py -q`.
- [ ] **Step 4: Verificar não haver publicação real** em testes automatizados, documentar e commitar.

### Task 14 — Histórico, erros, continuidade e edição do futuro

**Files:** Modify `api/routers/campaigns.py`, `api/routers/posts.py`, `frontend/src/components/posts/PostDetailsModal.tsx`, `frontend/src/pages/PostsPage.tsx`; tests `tests/api/test_post_schedule_slots.py`, `tests/api/test_campaigns.py`.

**Interfaces:** Produces: `GET /campaigns/{id}/occurrences`, status simples user/técnico ADMIN, vínculo `campaign_id` na listagem de posts e operações futuras condicionadas a revisão/status.

- [ ] **Step 1: Testes RED** de histórico imutável, `last_published_at` baseado no sucesso confirmado, falha que não impede slot seguinte e edição de apenas futuras.
- [ ] **Step 2: Rodar falhas, implementar e executar suite verde**, sem quebrar detalhes de postagem única.
- [ ] **Step 3: Atualizar UI com informação sutil e acessível**, documentar e commitar.

## F6 — Validação, documentação e promoção controlada

### Task 15 — QA, versionamento e evidências

**Files:** Modify `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/TASK.md`; create `docs/POSTS-CAMPANHAS-RESULTADOS-20261102.md`; `VERSION` só no release aprovado.

- [ ] **Step 1: Rodar frontend build e testes**: `cd frontend && npm run build`, `node --test frontend/tests/*.test.mjs`, `pytest tests/api tests/scheduler -q` (ajustar somente conforme dependências disponíveis).
- [ ] **Step 2: Registrar resultados reais** com hashes de commits/CI e ambiente, diferenciando mock/integração/staging-live/publicação externa.
- [ ] **Step 3: Conferir migrações aditivas**, RLS/índices, isolamento usuário/perfil, Storage, roles, conta `RafaelTesteCliente`, agenda do cron Supabase e logs sem divulgar segredos.
- [ ] **Step 4: Revisar visual e usabilidade desktop/Android**, calendário de 30 dias, itens sem cobertura, mídia por rede, seleção e recuperações.
- [ ] **Step 5: Abrir PR para staging e aguardar CI/deploy; pedir aprovação Rafa.** Somente após aprovação criar PR staging→main e bump correto de `VERSION`/release note.
- [ ] **Step 6: Manter backlog explícito pós-entrega** para TikTok Photo e tags/quota por plano.

## Builder check — ajustes incorporados antes da implementação

A revisão independente de 2026-11-02 identificou cinco zonas de falha. São ações vinculantes adicionais nas tarefas abaixo, sem ampliar escopo:

- **Task 1/2 (R15):** testar que staging insere/edita/cancela intenção no banco comum e produção a executa uma vez; provas SQL read-only e mocks de claim, auditoria dos dados marcados `environment=staging`, deployment sequencial sem executar duas cópias. A decisão de autoridade está na especificação §8.1.
- **Task 7/12/14 (R12):** teste de mudança de `revision` que recalcula apenas `pending` não-claimed, preserva snapshots de `running/succeeded/failed/unknown`, respeita novo ordenamento e expõe preview/diff para confirmação.
- **Task 10/13/14 (R05/R11):** fixtures por publicador/rede para ausência de credencial, mídia rejeitada, 429, 403, sucesso, falha, partial e unknown; testar agregação `postado`/`erro parcial`/`erro`/`sem confirmação` e continuidade da sequência.
- **Task 5/6 (R06):** subida manual de múltiplas mídias é entregável parcial em branch; captura automática de várias imagens Shopee não é considerada concluída sem fonte autorizada ou alteração explícita de requisito pelo Rafa.
- **Task 9/11 (R08/R10):** índices internos são 0-based; testes de janela sem slots, meia-noite inválida, data passada, fim não alinhado, horário ambíguo e múltiplas redes. Não ativar campanha sem slots futuros ou com violação de restrições.

## Regras de sequência e checkpoints

1. Documentação acima é a referência; não começar task posterior sem testes e aceite técnico da anterior quando dependente.
2. Antes de modificar código, verificar `AGENTS.md`, Guia Mestre, RULES, PRD, ARCHITECTURE, `VERSION`, `CHANGELOG.md` e contratos específicos.
3. Cada tarefa adota RED→GREEN→refactor, commit focado e atualização de `CHANGELOG.md [Não lançado]`.
4. Todo deploy/migração no Supabase compartilhado exige compatibilidade retroativa entre staging (adiantado) e main (versão atual).
5. Nenhuma mudança de `main` sem aprovação do Rafa; nenhum teste de publicação externa sem autorização.
6. Se a Shopee não disponibilizar fonte oficial com múltiplas imagens, registrar evidência e pedir alternativa autorizada; não declarar F2 pronta sem ela.
