## 03/11/2026 — F4E-2B2 (preparação; pendente CI, PR e deploy)

- [x] **Decisão de Rafa:** downgrade Premium→Pro pausa **todas** as campanhas até escolha de até 2 por perfil. Histórico e restantes permanecem preservados; sem reativação automática. Nenhuma campanha executável existe hoje.
- [x] Identidade F4E-2B2 corrigida para UUID em `schedulers.id` e `publish_jobs.id`, INTEGER em `posts.id`, rede permitida; bloqueio de envio continua incondicional. Testes de contrato preparados.
- [x] Proposta SQL de vínculo persistente inerte salva **fora** de `database/migrations`; não foi aplicada e não concede INSERT nem execução, apenas SELECT ao service_role. [Escopo e riscos](F4E-2B2-IDENTIDADE-INERTE-20261103.md).
- [ ] **Antes de executar:** PostgreSQL/concorrência, imutabilidade dos pais, controle no claim/retry/recovery/pré-envio, compatibilidade main/staging, OAuth, Storage real, quotas por rede/dia, T−30 e revisão service_role. Migração, promoção de `main`, reservas e teste de postagem dependem de aprovações separadas.
- [ ] Registrar PR/SHA, CI e staging LIVE apenas depois de evidência. Produção intacta; `VERSION=3.0.0`.
- [x] Gatilho de SMTP revisto no Vault: nenhum domínio próprio registrado **e configurado** comprovado para Auto Orbital; nenhuma alteração em e-mail.

## 03/11/2026 — F4E-2A (fechamento pós-deploy, staging somente)

- [x] **F4E-2A STAGING LIVE (03/11/2026, substitui nota histórica PRE-DEPLOY):** [PR #231](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/231) integrada somente em `staging` no squash `8e0c6b44f84d4fedb9951ef589369127ecaab407`; [CI #773 SUCCESS](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41707521280) (API 1.170, scheduler 175 + 1 xfailed, SQL 4, segurança/web 27, build frontend e PostgreSQL 16 isolado). Render `dep-dbl3ov15efls73bmmpd0` LIVE no mesmo SHA. Navegador após deploy: `GET /api/health/ready` = `{"status":"ok"}`; `GET /api/campaigns/drafts/11111111-1111-1111-1111-111111111111/preflight?expected_revision=1` sem sessão = `{"detail":"Não autenticado"}`. Supabase compartilhado: `campaign_reservations_f4e` = 0, `campaign_occurrences_f4e` = 0 após deploy. Preflight permanece exclusivamente leitura e parcial (`reservation_available=false`, `reserved=false`, `activated=false`, `checks_complete=false`), sem jobs, reservas, mídias, redes, migração nova nem postagem. `main` não foi alterada. Próximo gate F4E-2B: proteger caminho central/legado de execução e pré-envio com vínculo imutável fail-closed e flags OFF, mais mídia persistente, cota transacional por rede e conta, `service_role`, OAuth, congelamento T−30 e downgrade. Autorização separada obrigatória para qualquer promoção a `main`, reserva ou teste externo. [Vault PR #43](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/43) documenta os riscos.

> **F4E-2A PRE-DEPLOY (PR #231):** preflight autenticado de leitura parcial para rascunho e revisão, política de plano, cronograma e volume por rede. Retorna `preflight_only`, `checks_complete=false`, `reservation_available=false`, `reserved=false`, `activated=false`; não reserva, não chama RPC, não gera jobs/posts e não prova OAuth, retenção física de mídia ou vaga concorrente. Antes de qualquer reserva/execução: proteger mídia e rascunho contra exclusão concorrente, rever writes diretos service_role e validar guardas de dispatch em ambos ambientes. CI, revisão e deploy ainda não confirmados neste registro; `VERSION=3.0.0`.

> **03/11/2026 — Fechamento operacional F4E-1: integrada em staging e LIVE (atualização posterior ao PR draft).** [PR #229](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/229) squash `24c45b671e416d071c80c1c914eecaf6344db0b9`, [CI #764 SUCCESS](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41702740725) com PostgreSQL 16. Render `dep-dbl3aibbc2fs738kfllg` LIVE nesse SHA; navegador confirmou `/health` e `/api/health/ready` = `{"status":"ok"}`. A migration `20261103191911` está aplicada ao Supabase compartilhado e a `074_f4e1_inert_campaign_reservations.sql` registrada uma vez em `public.migrations` (boot seguro); reservas e ocorrências 0/0 pós-deploy, RLS ativo sem policies, acesso anon/authenticated negado. **Não há executor F4E, campanhas ativadas, agendamentos/jobs/posts ou cobrança; sem promoção de código a main/produção.** F4E-2, barreiras de dispatch, validação por rede/OAuth/mídia, decisão de downgrade e QA de planos são tarefas futuras sujeitas a nova aprovação. Rafa confirmou em mobile tags, mensagens, criação e separação de perfis; escolha de planos ainda indisponível. `VERSION=3.0.0`. Esta nota de fechamento prevalece sobre qualquer registro histórico abaixo que diga “PR draft”.

> **03/11/2026 — F4E-1: DDL inerte aplicada ao Supabase compartilhado, ainda em PR draft.** Por coordenação de Rafa, a migration Supabase `20261103191911 / 074_f4e1_inert_campaign_reservations` foi aplicada; `public.migrations` recebeu `074_f4e1_inert_campaign_reservations.sql`. A inspeção reportada após a aplicação encontrou zero reservas e ocorrências, RLS ativo sem policies, anon/authenticated sem acesso e service_role com SELECT/RPC, sem DELETE. Draft legado preservado. Não foram criados jobs F4E, executor ou publicações, nem houve merge ou deploy de main/produção. [PR draft #229](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/229); [CI #755](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41701678290) verificou a proposta anterior. Rafa confirmou em mobile apenas tags, mensagens e perfil; QA visual completo em desktop não foi comprovado, e escolha de plano permanece futura. F4E-2, validação por rede e retenção física de mídia continuam pendentes. VERSION permanece 3.0.0. Esta nota prevalece sobre estados anteriores abaixo.

## 03/11/2026 — Fechamento verificado F4D staging e limite de segurança F4E

- [x] 03/11/2026 — F4D **integrada apenas em staging**: [PR #219](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/219) squash `9adbd5a455022acecc580c7daba75bd445a8ec22`, [CI #728](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41696637695) SUCCESS (API 1.165; frontend 38 contratos + TypeScript/Vite; scheduler 175 + 1 xfailed; SQL 4; segurança/web 27; externo skipped esperado). Render staging `dep-dbl2obp5efls73f9durg` LIVE no mesmo SHA; browser confirmou `/health` e `/api/health/ready` como `{"status":"ok"}`. UI autenticada desktop/mobile ainda não verificada. Nenhuma migration/SQL/ativação/job/post externo, cobrança ou alteração de `main`/produção. `VERSION=3.0.0`.
- [x] Fonte da conta e ADMIN server-side, leitura de uso sem contagem fictícia; Free bloqueado em novas campanhas, legado de consulta/exclusão preservado; limites Pro/Premium apresentados. Automação indisponível; upgrade apenas informativo.
- [x] F4E auditada somente leitura: dispatch central de produção pode reivindicar agendamentos com origem staging se a configuração de dispatch estiver habilitada (flag real Render não verificada); separar F4E-1 inerte/transacional de F4E-2 execução protegida e não inserir campanha em `schedulers`/`publish_jobs` antes de guardas simultâneos nos dois ambientes. Não houve DDL nem autorização de ativação.
- [ ] Inspeção visual autenticada desktop/mobile e QA de perfil/downgrade; sem postagem real. F4E-1 exige autorização específica para migração aditiva compartilhada; F4E-2 exige autorização separada para executor e risco cross-env.

## 03/11/2026 — F4D: interface de plano e acesso (PR isolada, sem deploy)

- [x] Preparados badge de conta (alias Plus→Pro), ADMIN por resposta de servidor, resumos de uso/limite e locks contextuais no design system PT-BR.
- [x] GET autenticado read-only `/profiles/usage`, counts exatos por escopo, política server-side sem cache, null para consumo não comprovado de Agora/cron/ativas.
- [x] Free bloqueado para novas mutações/prévia de campanha, preservando consulta/exclusão legada; caps do servidor em datas/frequência. Automação visível, não operacional, CTA informacional sem preço/checkout.
- [x] Contratos executáveis frontend (helpers, hook escopado, SSR erro/loading, responsive/a11y, downgrade e teaser) e backend (escopo, ADMIN, null/zero, 503, auth e downgrade) preparados no gate CI.
- [x] CI #726 do primeiro HEAD `d3a4339` aprovada (frontend contratos + TypeScript/Vite, API, scheduler e segurança); staging externo corretamente skipped.
- [ ] CI completa do HEAD final, revisão e visual desktop/mobile/autenticado antes de merge/deploy staging; nenhuma postagem real de teste. Esta nota não declara deploy aprovado.
- [ ] F4E permanece bloqueada para ativação: reserva transacional, idempotência, T−30 e isolamento de ambientes precisam de entrega própria. Nenhuma migration/SQL, job, scheduler, Supabase, Vault ou main alterados por F4D.
- [x] VERSION=3.0.0 preservada. Gatilhos condicionais consultados no TASK vivo: sem evidência de domínio próprio registrado e configurado; SMTP permanece condicional. Vault e rollout coordenados pelo agente principal.
- Contrato: [F4, seção 10](PLANOS-F4-POLITICAS-E-FASES-20261103.md#10-f4d--interface-de-plano-consumo-e-acesso).

## 03/11/2026 — Fechamento operacional F4C2 em staging (sem ativação de campanhas)

- [x] [PR #217](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/217) integrada **apenas em `staging`** por squash `d80f60d289c314064fa6ac728c4b23f898a767c2` após [CI #722](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41692608479) **SUCCESS**: API 1.157 testes, scheduler 175 aprovados + 1 xfailed, SQL 4, web 27, frontend e build aprovados.
- [x] Render staging deploy `dep-dbl2d1k9v7es73datmag` **LIVE** no mesmo SHA; verificação por navegador sem login: `/health` e `/api/health/ready` ambos `{"status":"ok"}`. O CI e o health não validam fluxo autenticado nem publicação social real.
- [x] Enforce de Free sem novas campanhas, Pro 15 dias/3 envios por rede/dia, Premium 30/15, ADMIN bypass comercial, escopo/ownership e downgrade. `GET /campaigns/limits` sinaliza consumo de ativas `null` e disponibilidade de ativação/automação `false`.
- [ ] Quota de **Pro2/Premium5 campanhas ativas por perfil** será reservada de forma transacional na F4E, antes de existir ativação/qualquer job. Interface de acesso e upgrade é F4D. Nenhum SQL/migration 074 aplicado; produção `main` e `VERSION=3.0.0` preservadas.
- [ ] QA autenticada da campanha, concorrência real e testes de rede social permanecem pendentes, sem enviar posts só para demonstrar sucesso. Gatilho SMTP revisado: não há evidência de domínio próprio registrado **e configurado** no site.
- [x] Atualização documental de fechamento registrada neste PR separado, preservando histórico do desenvolvimento anterior.

## 03/11/2026 — F4C2: histórico de preparação pré-merge

- [x] Código preparado com autoridade de conta/política auditada, fail-closed, ownership e limites de prévia/rascunho/upload. Free mantém leitura/exclusão de legado; volume por rede e data local validado quando a agenda está presente.
- [x] Contratos unitários adicionados; sintaxe Python validada em memória. Runtime local sem FastAPI; CI ainda não confirmada nesta revisão documental.
- [ ] F4C2 é **parcial**: quota simultânea Pro2/Premium5 persistida na política, mas reserva atômica de campanha ativa depende da F4E. Nenhuma ativação/automação real é oferecida; endpoint de limites retorna consumo ativo null e disponibilidade false.
- [ ] Aguardar CI/revisão e autorização própria antes de merge/deploy staging. Sem SQL/migration 074, sem dados alterados, sem publicação real e sem main/produção. F4D frontend fora do escopo. VERSION=3.0.0.
- [x] Gatilho SMTP reavaliado com Vault TASK vivo: nenhum domínio próprio registrado **e configurado** comprovado; manter pendência condicional.
- Contrato detalhado: [matriz F4, seção 8](PLANOS-F4-POLITICAS-E-FASES-20261103.md).

## 03/11/2026 — F4C1 integrada e operacional em staging (evidência pós-merge)

- [x] PR #215 squash-merge apenas em staging SHA `397f0f760570c7aa39a1756f6a9e05deaf205d2f`, CI #717 verde, migration 073 autorizada e aplicada (Supabase `20261103175106`, `public.migrations` id=68), Render `dep-dbl20fss728c739c6kag` LIVE, `/health` e `/api/health/ready` = `{"status":"ok"}`. Sem post externo nem promoção `main`/produção; `VERSION=3.0.0`.
- [x] Tabelas novas de cota iniciaram vazias, RLS ativo, anon/auth sem acesso, RPCs SECURITY INVOKER só service_role; startup ignorou 073 registrada e iniciou scheduler.
- [x] Vault documentado na PR #38, squash `20490e3115e04f8f3295c9ed1adef322bfd40e70`.
- [ ] UI autenticada, concorrência real e publicação externa não testadas. Próxima etapa F4C2 campanhas/automação, depois F4D–F4F.

## 03/11/2026 — F4C1: limites de Agora e recorrência (branch isolada, SEM deploy)

- [x] F4B/F4B2 recuperada da interrupção: migração 072 aplicada e registrada no Supabase em 03/11, políticas Free1/Pro3/Premium5 perfis e cotas de catálogo/listas verificadas, RLS/grants de RPCs corretos; PR [#214](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/214) squash-merge apenas em staging (`83d8373`), CI #711 SUCCESS e Render `dep-dbkp2lu7bikc7397nir0` LIVE. `main`/Render produção preservados. Startup registrou 072 em `public.migrations`.
- [x] Branch `feature/f4c1-publication-quotas-20261103`: reserva por rede para Agora (janela de 60 minutos) e por dia+horário para cron, com lock transacional por conta, bypass comercial ADMIN e função de compensação apenas antes da execução. Considera agendas existentes para não permitir novos slots acima da cota; produção antiga continua sem trigger comercial global.
- [x] Rafa aprovou 073 e merge somente staging em 03/11; migração `073_post_publication_plan_quotas.sql` **aplicada** no Supabase compartilhado (histórico Supabase `20261103175106`), duas tabelas vazias, RLS ativo e sem SELECT anon/auth; RPCs invoker só service_role. Registro único em `public.migrations` (`id=68`) confirmado antes do merge; smoke de compensação sem usuário retornou 0, sem escrita comercial.
- [x] PR [#215](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/215) aberta em DRAFT; primeira CI [#713](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41600584554) falhou em 15 testes legados porque FakeDB não simulava a nova RPC; fixture corrigida sem afrouxar a validação real. CI [#716](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41601384035) **SUCCESS** no último SHA anterior aos commits documentais. Antes da aplicação, leitura confirmou 073 ausente.
- [ ] PR #215: CI do HEAD documental, merge **somente staging**, Render LIVE e smoke/QA sem disparo real. F4C2: campanhas ativas e automação, e F4D–F4F em entregas seguintes; `VERSION=3.0.0` sem release.

## 03/11/2026 — F4B2: limites de perfis e isolamento por conta (em homologação)

- [x] Rafa confirmou Free = **1 perfil total / 0 secundários**; Pro = **3 totais**; Premium = **5 totais**; ADMIN sem limite comercial. Produtos, Shopee, Gemini/IA compartilhados entre perfis. Listas **permanecem isoladas por perfil** (decisão expressa). Redes/OAuth, posts e históricos isolados por perfil.
- [x] PR #214 mesclada em staging (`83d8373`), migração 072 aplicada no Supabase e registrada em `public.migrations`, CI #711 verde, Render staging LIVE; produção antiga conserva teto 3 no trigger global e `main` não foi alterada. Sem publicação externa.
- [ ] F4C: enforce envios imediatos, recorrente, campanhas simultâneas e automação. Interface de upgrade e rollout `main` ficam separados.

## 03/11/2026 — F4B: quotas persistidas no backend (em execução)

- [x] Rafa fixou Premium em 2.000 produtos/conta, 100 listas/perfil, 5 envios imediatos/hora, 5 horários recorrentes/dia; Pro em **2 campanhas simultâneas/perfil**, Premium em **5**; cada rede publicada = 1 postagem. Substitui explicitamente o Pro=0 anterior.
- [x] `feature/f4b-backend-entitlements-20261103`: política SQL editável/auditável, source-of-truth por conta, RPC atômica produtos/listas/perfis, tratamento HTTP e testes; PR #214, CI #711, migration 072 e Render staging verificados.
- [ ] Próxima subfase F4C: guardas de perfis, recorrente, envio imediato, campanhas ativas, automação e UI. Não executar publicação real. Migração/DB compartilhado exige prova de compatibilidade com main.

## 03/11/2026 — F4A planos, etiquetas e política configurável (em homologação)

- [x] Decisão de Rafa organizada em matriz e fases: Free/Pro/Premium, ADMIN sem cotas comerciais, perfil, produtos/listas/posts/recorrente/campanha/automação e acesso comum; ver [contrato F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md).
- [x] Consulta read-only ao Supabase: `profiles.plan_tier` aceita `free|plus|premium`; `users.access` distingue USER/ADMIN; três perfis no momento da leitura. Teste `RafaelTesteCliente` (USER) mudou apenas perfil principal `free` → `premium`; releitura confirmou. ADMIN `rafastudio` permaneceu `ADMIN` e tag legada `free`.
- [ ] Branch `feature/plan-tiers-f4a-20261103`: etiqueta visual `Plus` → `Pro` com compatibilidade e badge Administrador quando papel validado; aguarda PR/CI/merge somente staging, sem enforce de cotas nesta fase.
- [ ] F4B–F4F: tabela de entitlements editável e auditável, migração compatível, guardas de backend por conta/perfil, UI bloqueada com upgrade, ativação idempotente e T−30; detalhes na especificação.
- [ ] Rafa precisa confirmar tetos Premium (produtos, listas, envio agora, recorrente), cota de campanhas criadas/ativas e unidade de contagem de envios multirrede. Não assumir ilimitado nem habilitar disparo externo.
- [x] `VERSION=3.0.0`; `main` e produção inalteradas. Gatillho SMTP ainda depende de prova de domínio próprio registrado e configurado.

## 03/11/2026 — F3C: postagens/dia e botão Excluir rascunho (PR #211)

- [x] Pedido do Rafa: substituir campo `Intervalo (min)` por seletor **1 a 15 postagens/dia**, mantendo datas (máximo absoluto de 30 dias inclusivos), dias da semana e janela horária; distribuição uniforme via `plan_campaign_slots`.
- [x] API `POST /campaigns/preview` e salvamento de rascunho usam `posts_per_day`; valor fora de 1–15 ou janela curta rejeitados no backend. Rascunhos locais/servidor antigos com `interval_minutes` são convertidos no frontend com teto 15 e aviso para revisar prévia.
- [x] `DELETE /campaigns/drafts/{id}?expected_revision=...` verifica usuário/perfil/status/revisão, bloqueia mídias em upload, valida prefixo do Storage e remove objetos privados antes do registro; o frontend exige confirmação inline. Não afeta lista-fonte nem posts/jobs.
- [x] Sem migration Supabase, sem mudança em `main`, produção, publicadores, credenciais, plano ou versão `VERSION=3.0.0`; não ativar campanhas nesta PR.
- [x] PR [#211](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/211) squash merge exclusivamente `staging` `140ea06d7af804b4c3ad1b2547751334dc972d89`; CI [#41581370451](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41581370451) SUCCESS; Render `dep-dbkmmf7lk1mc73e1o2p0` LIVE, migration 071 já aplicada, startup completo e `/health` = `{"status":"ok"}`. Vault TASK e checkpoint 62 atualizados.
- [ ] Nova aba de staging exigiu login; não houve revisão visual autenticada F3C nem exclusão real de dados de Rafa. Testes de API/Storage e UI por CI. Próximo incremento isolado: ativação com quotas por plano/rede, idempotência e edição T−30; não confundir prévia com publicação.

## 03/11/2026 UTC — Fechamento F3B em staging (PR #209, schema 071)

- [x] Migração `campaign_names_media_071` aplicada ao Supabase compartilhado com autorização, com default de nome para compatibilidade com backend antigo, tabela `campaign_draft_media`, RLS/grants restritos, trigger de propriedade e bucket privado. Migrador interno reaplicou SQL reentrante no boot sem falhar.
- [x] CI [#41578367282](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41578367282) SUCCESS; PR #209 squash merge exclusivamente `staging` `5ec24df`. `main`, produção e `VERSION=3.0.0` não promovidos.
- [x] Render staging `dep-dbkm74ks728c738ritc0` LIVE no SHA correto; logs migration 071 aplicada / Application startup complete; navegador `/health` = `{"status":"ok"}`.
- [x] UI autenticada em `/posts/criar`: nome no topo, recuperação de rascunho existente pelo nome, opção de foto Shopee e seletor de anexos por produto. Nenhum post/job real disparado.
- [ ] Upload/remover mídia REAL end-to-end exige teste de arquivo controlado; CI já validou upload sanitizado/isolamento e frontend. Não criar artefatos de teste no perfil de Rafa sem limpeza planejada.
- [x] Registro operacional consolidado no Vault [checkpoint 62](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/62-F3B-Nome-Campanha-Midia-Duravel-2026-11-03.md).
- [ ] Etapa seguinte: ativação transacional de campanhas, cotas por plano/rede, proteção T−30 e política anti-spam; fora desta entrega.

## 03/11/2026 UTC — F3B: nome próprio e anexos persistentes da campanha (branch isolada, SEM merge)

- [x] Pedido de Rafa: cada campanha terá nome personalizado, independente da lista, identificável na recuperação por servidor. Contrato 1–120 caracteres e validação backend/frontend.
- [x] Editor por produto: anexos de foto/vídeo do PC/celular, até 10 arquivos de 50 MB por produto, sanitização existente, armazenamento privado `post-media`, listagem/remoção por campanha e perfil. Foto principal Shopee continua disponível.
- [x] Preparada `071_campaign_names_and_media.sql` aditiva e reentrante, com RLS, vínculo de dono/produto, slots únicos. **Não aplicada ao banco compartilhado**; migrador no boot exige autorização antes de qualquer merge `staging`.
- [x] Testes objetivos de nome, ownership do produto e integridade estática/idempotência da migração; CI da PR será o gate.
- [ ] CI e revisão da branch/PR; pedir autorização específica para schema 071, aplicar/validar, só depois merge `staging` e conferir Render health. `main` e produção app intocados.
- [ ] Fases seguintes: ativação atômica, limites de plano/criação e por rede, congelamento T−30 e exceções TikTok, em incrementos separados. **Não há disparo em F3B**.
- Registro técnico: `docs/CAMPANHA-F3B-NOME-E-MIDIAS-20261103.md`. Histórico Vault a sincronizar ao fechar gate.

## 03/11/2026 UTC — Fechamento F3A e incidente de migração 070

- [x] PR [#207](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/207) mesclada só em `staging`; a migration 070 foi previamente aplicada com autorização.
- [x] No primeiro deploy, a aplicação reexecutou 070 e encontrou trigger duplicado; corrigido com guarda condicional e PR [#208](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/208), mesclada em `staging`.
- [x] Render staging depois de #208: deploy LIVE, migrador concluiu, aplicação iniciou, `/health` retornou `{"status":"ok"}`. Documentado no Vault #61. `main` inalterada.
- Regra permanente: inspecionar migrations e preparar DDL reentrante antes de aplicar ao banco compartilhado; merge para ambiente que inicia migrador apenas após autorização e gate.

## 03/11/2026 UTC — F3A: rascunho de campanha persistente (PR #207, schema 070 aplicado com autorização)

- [x] Branch `feat/campaign-persisted-drafts-f3a-20261103` isolada de `staging`, com PR [#207](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/207). `main` e scheduler de staging/produção intactos.
- [x] TDD: CI RED inicial 4 falhas por contrato ainda ausente; backend de rascunhos implementado com escopos de usuário/perfil, IDs exatos dos itens e versionamento otimista; schema 070 aditivo com RLS e trigger de ownership preparado.
- [x] Frontend: botão Salvar/Atualizar, lista e Carregar rascunhos por servidor na página `Criar POST`, com cópia local preservada e layout responsivo. Nenhuma ação cria post, job, mídia ou ativação.
- [x] Garantir que o planejamento opcional use a mesma lista e ordem de produtos; snapshots antigos não editam a lista-fonte.
- [x] CI anterior [#41570799397](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41570799397) success (API e frontend); aguardar CI final com a migration ajustada para o gate de merge.
- [x] Rafa autorizou especificamente migration 070. Aplicada via Supabase `campaign_drafts_070` em 03/11/2026. Inspeção confirmou tabela vazia, RLS ativo, anon/authenticated sem SELECT, service_role com SELECT/INSERT, ownership trigger ativo. Nenhum post/job/agendamento criado.
- [x] PR #207 mesclada em `staging`, boot corrigido na PR #208 e Render LIVE/health OK. `main` intocada; `VERSION=3.0.0` continua até release planejada.
- [x] F3B desenvolvida em branch separada (não implantada): nome próprio e anexos por item (foto/vídeo PC/celular, foto Shopee preservada), com limpeza só de uploads incompletos. F4/F5 de ativação, cotas e regra T–30 vêm depois.
- **Limite conhecido:** a restauração editável requer lista de origem ainda existente e com os mesmos produtos; snapshots no banco sobrevivem à remoção da lista, mas a UI bloqueia carregamento quando isso poderia causar perda silenciosa.
- **Segurança:** nenhum segredo, token, item do cliente ou dados de campanha são transcritos no log documental.

## 02/11/2026 BRT (03/11 UTC) — F3 incremental: snapshots locais por item de campanha (PR #206)

- [x] Partir de `staging` após PR #205 e manter implementação isolada em `feat/campaign-item-snapshots-local-20261103` (PR #206), sem tocar em `main`, Supabase compartilhado ou publicação real.
- [x] Reusar a página `Criar POST`, o seletor de redes/estado das credenciais e tokens de CSS existentes; cada item de uma lista tem um snapshot local independente de título, texto, link de afiliado, versões por rede e escolha da foto principal Shopee. Ordenação e prévia read-only preservadas.
- [x] Persistir apenas **texto/metadados** no rascunho do navegador, com chave por usuário/perfil; proteger restauração contra IDs e redes de outras listas e preservar campos explicitamente apagados. O snapshot não altera a lista-fonte.
- [x] Contratos RED observados no [CI #41565293561](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41565293561): 3 testes falharam pela ausência inicial do modelo, como esperado. Incluído teste de snapshots no gate de frontend.
- [x] Contratos dos snapshots **32/32** no [CI #41565732655](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41565732655), mas build TypeScript inicialmente falhou em conversão de `Object.fromEntries` para `Record<PostNetwork, NetworkState>`; tipagem corrigida no commit `133591d`. **CI final e deploy staging devem ser verificados antes do merge e da conclusão.**
- [ ] UI e upload **persistente** de fotos/vídeos locais por item, edição/IA em lote, schema transacional/RLS, políticas de redes, cotas e ativação permanecem etapas separadas. Foto Shopee e upload PC/celular da publicação única seguem intactos.
- [ ] Prosseguir com merge da PR #206 somente após gate CI e revisão; **nunca promover `main` sem aceite específico de Rafa**. `VERSION` permanece `3.0.0`; release candidata ainda `3.1.0`.

## 02/11/2026 BRT (03/11 UTC) — Ícones Criar POST, CHANGELOG e governança de releases

- [x] Auditoria do menu: `PanelPage` referencia `square-pen`, não registrado em `Icon.tsx`; ação da campanha referencia `calendar-search`, também ausente. Corrigir registro de ambos sem alterar menu, rotas ou publicação.
- [x] Recuperar entrada de `[Não lançado]` para PR #204, ausente após merge; incluir correção dos ícones e teste que impede referência a ícones inexistentes.
- [x] `VERSION=3.0.0` lido em `frontend/vite.config.ts`, é fonte real de versão exibida no site; manter enquanto não houver release formal e aprovado. **Candidato 3.1.0** (MINOR compatível), não confirmado como release.
- [x] Verificado em `AGENTS.md`/`RULES.md`: branch isolada → PR staging → CI → Render live → aceite → PR staging→main → CI/deploy/health. Última comparação antes desta correção: `main` e `staging` divergem (13 commits à frente em staging, 8 na main e alterações em vários módulos). **Não mesclar lote inteiro em produção sem revisão e autorização de Rafa.**
- [ ] Após CI e Render da correção do ícone, preparar inventário da promoção, classificar o lote e solicitar aprovação explícita da release. Só então incrementar `VERSION` nas branches por PR, fechar `CHANGELOG` e publicar com health.
- [ ] Validar em staging o novo ícone visível no rail; preservar página de campanha e seus endpoints somente leitura.

## 02/11/2026 — Regularização de SemVer: Auto Orbital 3.0.0

- **Decisão expressa de Rafa:** oficializar `3.0.0` em `staging` e `main`, mantendo `VERSION` como única fonte da versão da aplicação e `CHANGELOG.md` obrigatório em toda alteração/PR.
- **Justificativa MAJOR:** o fluxo atual não aceita mais múltiplos produtos no novo post e removeu a criação de agendamento avulso; legados seguem preservados. O salto de `2.7.0` para `3.0.0` consolida mudanças já presentes na `main`, sem alterar sua lógica de execução nesta tarefa.
- **Governança futura:** PATCH para correções de bugs/desempenho/segurança sem alterar regras de negócio, MINOR para funcionalidades compatíveis, MAJOR para quebras. Atualizar `[Não lançado]` por PR, fechar o changelog e incrementar versão na entrega aprovada; documentações isoladas não forçam nova versão.
- **Documentação-alvo:** `VERSION`, `CHANGELOG.md`, `README.md`, `AGENTS.md`, `docs/RULES.md` e este `TASK.md`.
- **Validações necessárias:** CI da PR em staging; conferir `VERSION` e `CHANGELOG` implantados em ambas as branches, depois CI/deploy/health da produção. Nenhum OAuth, token, banco, agendamento ou post real será alterado/testado por esta regularização.
- **Pendências independentes:** erro externo Threads 403, publicação real E2E e adequação da arquitetura ao despacho centralizado em produção continuam fora desta alteração de versão.

## 02/11/2026 — IDs dos posts, concorrência e isolamento por cliente (staging)

- [x] Confirmar no Supabase que `posts.id` é SERIAL global, crescente e não reutilizável; editar preserva ID, inclusive com exclusão posterior. Auditoria read-only: 0 desvios de usuário/perfil nas relações post→agenda→ocorrência e partes de thread.
- [x] Exibir `#ID` discreto à esquerda dos posts e no modal de detalhes; remover fusão de posts antigos por timestamp/texto (só `group_id`).
- [x] Fortalecer conflito de idempotência e claim da fila para exigir identidade de usuário/perfil/post/agenda/rede; recursão de posts, agendamentos e leitura protegidas por dono/perfil; separar sucesso na criação de falha do disparo “Agora”.
- [x] Adicionar testes de mesmo horário para múltiplos posts de um cliente e clientes/perfis diferentes, escopos SQL, UI e edição preservando ID.
- [ ] Revisar CI/PR e staging; **não publicar posts reais** nos testes.
- [ ] Para testar publicação recorrente em staging: **isolar jobstore/fila/banco** do ambiente de produção com autorização e avaliar custos. Com Supabase compartilhado, scheduler de staging segue desativado e o aviso de indisponibilidade permanece correto. Sem alterar `main`/produção.
- **Guia:** `docs/POSTS-IDENTIDADE-CONCORRENCIA-20261102.md`.

## 02/11/2026 — Falha de recorrência Threads no staging: scheduler 503

- **Incidente (04:43 UTC):** importação de foto 201, preview 200, lote 201 com Threads bloqueado; bridge `create_scheduler_job` retornou HTTP 503 antes de registrar o primeiro horário. Agendador de staging sem iniciar desde 30/10; produção tem scheduler ativo e Supabase compartilhado.
- **Correção:** preflight da disponibilidade no frontend/API, status interno privado read-only, desabilitar Criar com aviso claro e preservar rascunho; nenhum job/post/arquivo novo quando scheduler indisponível. **Não habilitar scheduler do staging sem isolamento e autorização.**
- **Referência:** `docs/POSTS-SCHEDULER-503-20261102.md`, testes em `tests/api/test_recurring_scheduler_bridge.py`, `tests/web/test_internal_func_whitelist.py` e frontend.
- **Pendência:** homologar staging/CI e definir execução segura por ambiente antes de testar publicação real. `main` intocada.

## 02/11/2026 — Rascunhos locais persistentes nos formulários (somente staging)

- Pedido de Rafa: persistir o formulário ao fechar modal, atualizar, perder conexão ou reiniciar navegador, inclusive reconhecer remoção intencional de texto e **não ressuscitar o valor antigo**.
- Implementado: armazenamento local versionado e isolado por conta/perfil/tipo de formulário, recuperação no retorno, limpeza só após sucesso do backend; posts, produtos, catálogo, listas, perfis, usuário admin sem senha, preferências não secretas das credenciais, filtros e buscas; `File`, tokens e credenciais excluídos.
- Documentação e bateria de testes: `docs/FORM-DRAFTS-PERSISTENCE-20261102.md` e `frontend/tests/form-drafts.test.mjs`.
- **Homologação:** validar CI, staging implantado e QA com sessão autenticada; nenhum deploy na main/produção e nenhuma postagem real de teste.

## 02/11/2026 — Descrições IA e mídia individual por rede (somente staging)

- Correção da geração que devolvia Threads acima de 500 caracteres e seis hashtags apesar de retry; tratamento determinístico com revisão e link preservado.
- Um texto por rede escolhida com abas individuais; resumo de mídia esclarece subset, texto sem mídia e redes excluídas.
- Documento técnico: `docs/POSTS-COPY-IA-POR-REDE-20261102.md`.
- Android e usuário USER: aprovados conforme relato de Rafa; Threads: acompanhamento de agendamentos pelo usuário, sem publicações de teste.

## 02/11/2026 — Complemento pós-deploy staging: falha histórica 403

- [x] CI #521 **verde** no PR #181; deploy staging `dep-dbk0blfavr4c73cj0srg` SHA `4ffc0f7` **live**; `/api/health/ready` respondeu `{"status":"ok"}`.
- [ ] Correção adicional em PR: erro HTTP 403 legado do primeiro contêiner (com `published_parts=0` e prova temporal/scheduler) reaparece como **Erro** no dia/hora correto. Sem reenvio externo; demais desconhecidos continuam sem confirmação.
- [ ] Validar visualmente os modais e testar credenciais Threads autorizadas. Produção intocada.

## 02/11/2026 — Posts: produto único, só Agora/Recorrente, horários, status e privacidade — STAGING / EM VALIDAÇÃO

- [x] Código de correção isolado em `fix/posts-recorrencia-20261102`, PR para `staging`; não alterar `main`.
- [x] UI: rádio para exatamente zero ou um produto, sem selecionar lista em massa; hora desktop 24h e atalhos, Android nativo.
- [x] API: máximo um `product_id`; novos agendamentos avulsos são rejeitados. `trigger=date` interno necessário para Agora e legados, sem migração por Supabase compartilhado.
- [x] Detalhes: `schedule_slots` por dia/hora e estado real via `publish_jobs`; `last_published_at` independente da última execução; erro simples USER e diagnóstico ADMIN.
- [x] Threads: erro 403 agora captura code/subcode da Meta sem URL/token; 4xx confirmado na criação de contêiner classificado failed, publish ambíguo continua unknown.
- [ ] CI, revisão de desktop e Android, validação da conta Threads e aceitação de Rafa. O 403 real não pode ser considerado resolvido sem código da Meta e autorização/reconexão, quando necessária.
- [ ] Deploy staging após CI e revisão; produção proibida.

Detalhamento em `docs/POSTS-AJUSTES-RECORRENCIA-20261102.md`.

## 02/11/2026 — Refinamento V3.2: cards 3D em staging, pendente de aceite estético

- [x] **Escopo de Rafa:** preservar integralmente as cenas/timeline/câmera/identidade da V3.1 e aprimorar somente as fichas de produto e propaganda, evitando aparência plana.
- [x] **Implementação isolada:** `fix/landing-pilot-3d-cards-v32`, PR [#174](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/174); apenas `Sheet`, estilos `ao3-sheet*` e testes de contrato, sem novas dependências.
- [x] **Correções de virada/visibilidade:** PRs [#175](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/175), [#176](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/176) e [#177](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/177). Face de divulgação agora é legível após rotação completa; transparência nas superfícies não achata o contêiner 3D.
- [x] **CI + Render staging live:** frontend (testes e build) e API verdes nas revisões; commit `2f8967d74bd5bff2195e18e494d35a74f995d7d8` ao vivo no staging.
- [x] **QA visual desktop:** capturas reais dos quadros 3.0s (volume das fichas), 5.6s (virada), 6.1s (verso publicitário visível) e 9.0s (assinatura final preservada).
- [ ] **QA móvel e aprovação de Rafa:** ainda não testado visualmente em viewport móvel nesta rodada; aguardar aceite estético. A V3.2 continua piloto provisório.
- [ ] **Promoção à landing principal e main:** não autorizada; manter a prévia em `/presentation/pilot` isolada.



## 01/11/2026 — Motion V3 PROCEDURAL / V2 REPROVADA

- [x] **Rafa reprovou a V2:** cartões colados, PNG do buraco negro e movimentos desconectados da narrativa. Não promover V2.
- [x] **Storyboard seis atos (0–10s) silencioso:** produto, tarefas, acúmulo, pausa, horizonte procedural, revelação do painel e assinatura, detalhado em PILOTO-LANDING-VIRADA-ORBITAL.md.
- [x] **Implementação em laboratório:** /presentation/pilot substituído por elementos Canvas 2D/DOM/CSS, sem imagens ou sons, sem dependência adicional.
- [ ] **QA da V3:** CI, revisão de quadros, independência das trajetórias, leitura mobile, redução de movimento, FPS, console e aceite de Rafa antes de mudar landing ou produção.
- [ ] **Marca gerada por código:** comparar assinatura procedural com master oficial. Como o master é bitmap, não declarar que CSS produziu cópia pixel-a-pixel sem certificação/aceite. A marca usada em produção não é alterada.

## 01/11/2026 — REPROVAÇÃO DA CENA V1 / PILOTO V2 HORIZONTE DE EVENTOS

- [x] **Feedback do proprietário:** V1 **descartada**; excessivamente lenta, transição/zoom superficial, letras paradas, sem jogos de câmera e sem vida. A referência correta da marca é o **buraco negro com horizonte de eventos**, papéis de **produtos** transformando-se em **propagandas** ao orbitar, metáfora de ciclo automático (visão futura, não funcionalidade pronta).
- [x] **V2 em branch independente:** `feature/rework-orbital-black-hole-cinematic-2026-11-01`; reconstrução da `/presentation/pilot` com o símbolo **oficial**, tipografia cinética por letras, perspectiva/câmera, cartões de dupla face, órbita e transições rápidas, 9,6s sem som. Ver [especificação da V2](PILOTO-LANDING-VIRADA-ORBITAL.md).
- [ ] **Portão de QA e homologação:** aguardar testes TypeScript/Vite e revisão visual no staging desktop/mobile; submeter ao Rafa. **Não integrar V2 à landing sem aprovação expressa.**
- [ ] **Automação total com IA:** permanece em desenvolvimento. Nenhuma promessa de disponibilidade ou mudanças na execução de postagens.

## 01/11/2026 — Landing: piloto visual da transformação orbital (isolado, sem áudio)

- [x] **Implementação em branch de trabalho:** `feature/landing-orbital-scene-pilot-2026-11-01`, baseada em `staging`; prévia interativa prevista em `/presentation/pilot`, sem qualquer modificação da landing aprovada (`/presentation`) ou da autenticação.
- [x] **Peça de estudo com marca oficial:** arte `/brand/wordmark.png` e `/brand/symbol.png` do design system; roteiro “caos → pausa → convergência → fluxo organizado → assinatura”, 10 segundos como hipótese de piloto, reprodução/pausa/reinício e scrub manual, **sem som**. Contrato no [documento técnico](PILOTO-LANDING-VIRADA-ORBITAL.md) e Vault [storyboard 43](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/29).
- [ ] **Gate de QA:** CI TypeScript/Vite, testes, inspeção real desktop/celular e `prefers-reduced-motion`; validar que a marca permanece fiel quadro a quadro. **Não alegar produção de vídeo final**: a cena atual é um protótipo visual React/CSS, não mídia exportada.
- [ ] **Gate de aprovação:** obter aceite visual de Rafa antes de qualquer integração da cena à landing aprovada ou deploy em produção. Sem custo, dependência externa ou troca de rotas existentes.

## 01/11/2026 — Futuro vídeo cinematográfico de apresentação no LOGIN (documentação, sem código)

- [x] **Decisão registrada:** Rafa quer substituir futuramente o vídeo atual da caixa em `/login` por uma animação premium original, com **logo oficial 100% fiel** e resumo visual de valor para afiliados; não aceita simples caixa/card e não autorizou implementar agora.
- [x] **Especificação técnica/QA:** [`docs/LOGIN-ANIMACAO-CINEMATOGRAFICA.md`](LOGIN-ANIMACAO-CINEMATOGRAFICA.md), complementada pelo [Vault 44](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/44-Planejamento-Animacao-Cinematografica-Login-Auto-Orbital.md). Documentação em branch e PR de revisão, sem efeito no site até integração.
- [ ] **LG.1 storyboard e direção fina — BLOQUEADO:** validar arte oficial, capacidades reais, copy com `vender-com-valor`, cenas desktop/mobile, poster, duração e proposta visual com Rafa.
- [ ] **LG.2 render/integração — NÃO AUTORIZADO:** protótipo silencioso; depois branch isolada de staging, testes login Supabase/Google/usuário de suporte Shopee, `prefers-reduced-motion`, carga de vídeo e fallback; aprovação explícita antes de `main`.
- **Arquivos de produção preservados:** `frontend/src/pages/LoginPage.tsx`, `LoginPage.css` e `frontend/public/videos/login-bg.mp4`. Sem alterar autenticação, vídeo, rotas ou dependências neste registro.

## 01/11/2026 — Correção do login temporário Shopee (PR #166, somente staging)

- [x] **Erro reproduzido:** Rafa tentou `RafaelTesteCliente` em `/login`, mas o campo HTML `type=email` bloqueou o envio antes de chegar ao backend. O link anterior “Acesso temporário para suporte Shopee” não era suficientemente evidente.
- [x] **Correção frontend:** campo único e identificado como “E-mail ou usuário de suporte”, HTML `type=text` só quando o modo de suporte estiver disponível; o formulário escolhe login por e-mail Supabase para identificadores com `@` e rota legada exclusivamente para o nome de usuário sem `@`. Quando Supabase Auth está desativado, mantém o login legado local original. Orientação visível e preservação da recuperação de senha por e-mail.
- [x] **Limite de segurança preservado no backend:** `POST /api/auth/login` continua exigindo correspondência estrita com `SUPABASE_LEGACY_SUPPORT_USERNAME`, papel `USER` e conta sem identidade Supabase Auth, com limite de tentativas; sem liberar Render Auth a outros usuários.
- [x] **Regressão automatizada:** `frontend/tests/support-username-login.test.mjs` incluído na CI, verificando o campo, direcionamento e whitelist do backend. CI [RED da falha original](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41345573736) (etapa frontend falhou antes do commit de implementação).
- [ ] **Gate antes de staging:** CI completa da versão final (frontend + API), revisão do PR e merge APENAS `staging` com deploy Render `live`.
- [ ] **Homologação de Rafa:** confirmar login real da conta `RafaelTesteCliente` com a senha existente; jamais coletar senha no chat nem alterar conta/credenciais apenas para teste. `main`/produção exigem ordem posterior.

## 01/11/2026 — Landing Auto Orbital, Fase 2 autorizada (somente staging)

- [x] Rafa autorizou a próxima fase das rotas após aprovação do protótipo desktop e primeira versão mobile. **Não há autorização de promoção à `main`/produção.** [Escopo e gates](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/blob/feature/landing-entrypoint-routes-2026-11-01/docs/superpowers/plans/2026-11-01-landing-entrypoint-routing.md).
- [x] Branch `feature/landing-entrypoint-routes-2026-11-01` a partir de `staging`, [PR #165](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/165). Fase 2: `/` mostra landing ao visitante anônimo; sessão real validada por `authApi.me()` encaminha USER a `/app` e ADMIN a `/admin/overview` (ou `/app` se optou explicitamente por visitar o site de cliente).
- [x] `/presentation` é landing pública estável para compartilhar inclusive para quem está logado; `/apresentacao` redireciona à nova rota. `/login` e `/admin/*` permanecem, assim como os caminhos atuais de produtos e posts.
- [x] Open Graph/Twitter Card no HTML inicial usam imagem pública de marca e **preservam o host compartilhado**; nenhuma URL canônica hardcoded redireciona staging para produção. `/app` excluído em robots.txt; resposta HTML de staging inclui `X-Robots-Tag: noindex, nofollow` antes do JavaScript. Proteção por cookie/papel continua exclusivamente no backend.
- [x] TDD remoto: RED da raiz no [CI #459](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41339768886), RED de compartilhamento no [CI #463](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41339976693), GREEN inicial no [CI #464](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41340196960), RED específico da resposta noindex no [CI #466](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41340727402). Aguardando GREEN final após correções.
- [ ] Conferir CI integral (API), revisão do PR, merge apenas em `staging`, deploy Render `live`, smoke público de rotas, links e redirecionamentos; testes autenticados USER/ADMIN/Google em navegador autorizado de Rafa. **Sem tocar Supabase/credenciais/posts de usuário.**
- [ ] Homologar com Rafa antes de qualquer promoção a `main` (produção). Preservar cópia, cenas, design system, persuasão e protótipo aprovado.

## 01/11/2026 — Landing Auto Orbital, Fase 1 aprovada: prévia pública em staging

- [x] Rafa autorizou expressamente a Fase 1; escopo canônico integral em [Vault/34-Planejamento](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/34-Planejamento-Landing-Publica-Auto-Orbital.md). Aplicar na narrativa as skills `criar-sites-imersivos-premium` e `vender-com-valor`.
- [x] Criada branch de implementação `feature/landing-preview-fase1-2026-11-01` a partir de `staging`. Nova rota pública `/apresentacao` não altera a rota `/` autenticada, o login ou os callbacks Google/Supabase.
- [ ] Finalizar e homologar a prévia com nove etapas narrativas, três cenas ilustrativas/placeholder de Scroll World, CTAs **Ver como funciona** (âncora para demonstração) e **Entrar** (`/login`), layout mobile e reduced motion. Textos distinguem recursos existentes, condicionados e em desenvolvimento; não incluir preços ou checkout.
- [ ] Registrar CI frontend/build, smoke anônimo HTTP da rota, navegação de CTA, inspeção visual desktop/mobile, sem mudanças em autenticação, API, banco, serviços adicionais ou produção. Somente depois submeter a Rafa para avaliação em staging.
- [ ] **PRINCIPAIS GATES FUTUROS:** vídeos definitivos, promoção de `/` para landing e dashboard `/app`, migração de rotas OAuth, cadastro/planos/cobrança e deploy em `main` dependem de planejamento adicional, QA e autorização separada de Rafa.

## 01/11/2026 — Placeholder de Automação de posts (apenas interface)

- [x] Criar rota autenticada `/automacao-posts` com página simples e texto **“Automação de posts em breve”**, reutilizando o design system (Mona Sans, painel escuro, cores e ícone Lucide).
- [x] Adicionar item **Automação** ao menu lateral, ícone `workflow`, junto à seção Posts, inclusive na navegação mobile existente.
- [x] Nenhum endpoint, agendamento, IA, coleta, publicação automática ou persistência adicional foi implementado nesta entrega.
- [ ] Definir com Rafa o escopo funcional, controles, limites, custos e fluxos de automação antes de desenvolver qualquer execução real.
- [ ] Homologar a página em staging e solicitar aprovação separada antes do merge para `main`.

## 01/11/2026 — Ajuste fino da listagem de Posts: compactação e recorrência ativa

- [x] Limitar a prévia do texto a uma única linha com reticências; exibir apenas o primeiro produto (+ quantidade adicional) e as redes de destino.
- [x] Reorganizar metadados em duas faixas compactas: etiquetas de tipo/execução e datas essenciais (criação, última tentativa e resumo do agendamento).
- [x] Em recorrências com registro de agendamento ainda existente, exibir **Em andamento**, inclusive depois de publicação concluída de uma ocorrência; manter simultaneamente o resultado da última execução (`Publicado`, `Falhou`, `Sem confirmação` etc.).
- [x] Mostrar resumo de dias/horários no card e preservar a agenda completa na visualização de detalhes e no texto pesquisável.
- [x] Não alterar modal de visualização, edição/criação, API, banco ou semântica de publicação.
- [ ] Homologar visualmente no staging após CI e deploy, sem publicar em produção.

## 01/11/2026 — UX de Posts: cards concisos, busca e detalhes somente leitura (PR #159 integrado ao staging em a55e48b; refinamento visual em andamento)

**Pedido de Rafa:** simplificar a listagem sem perder informações de execução, melhorar a busca enquanto se digita e impedir edição acidental de posts já construídos, agendados, recorrentes ou publicados.

- [x] **Cards compactos:** trecho curto do texto, nomes dos produtos, redes de destino, criação, tipo (imediato / agendado / recorrente), última publicação, data/hora do agendamento e todos os dias/horários de recorrência. Manter status de publicação e alertas de confirmação incerta.
- [x] **Busca instantânea:** filtrar por texto, produto, rede, data/hora (criação, programação, execução e recorrência) e recuperar páginas adicionais do histórico, respeitando conta/perfil. Não modificar dados em função da busca.
- [x] **Detalhes imutáveis:** clicar no card abre um modal **exclusivamente de leitura** com textos completos (inclusive múltiplas partes), produtos, mídias/rede, datas, horas, configurações e status. Remover desta visualização seletores de produto, edição de texto, geração com IA, botões de salvar/remover partes/mídia. Preservar o fluxo separado de **Novo post**.
- [x] **Proteção API:** bloquear alterações diretas nas postagens agendadas, recorrentes, imediatamente publicadas ou com histórico de tentativa/envio; preservar o processamento legítimo do scheduler, conciliação e exclusão explícita com confirmação. Não confiar exclusivamente no modal.
- [ ] **Homologação:** CI frontend/backend, testes de escopo entre perfis, caso de várias horas de recorrência, filtro de busca e smoke visual em staging. **Não executar publicação real, SQL, exclusões ou merge na main automaticamente.**

**Evidências:** [PR técnico #159](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/159) aberto contra `staging`. [CI #445](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41322243390) **sucesso** (API, frontend e testes novos; sem publicação real). Smoke visual e merge/staging **ainda pendentes**. A busca carrega páginas adicionais e filtra no frontend; otimização de consulta/indexação servidor deve ser reavaliada quando houver volume e métricas reais. Evitar confundir `last_result.at` de falha/registro manual com confirmação de publicação. [PR Vault #21](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/21).

**Governança:** branch `fix/posts-resumo-busca-detalhes-readonly-2026-11-01` a partir de `staging`; PR e evidências devem ser acrescentados após conclusão. Produção e banco Supabase compartilhado permanecerão inalterados nesta etapa. A aprovação de Rafa é necessária para promover à produção.

## Estado vigente — Supabase Auth publicado em produção (01/11/2026, 05:13 UTC)

- **Código/release:** PR [#155](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/155) integrado em `main` SHA `a6b87b3228db2164601225652d95b5bbbc38184c`; CI [#437](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41275819236) **success** (API, frontend e smoke de staging). PR #154 criou coexistência de login e PR #156 adequou o smoke; staging `1738c146`, deploy `dep-dbjcgjou01pc73f2scng` live.
- **Render produção:** serviço `shopee-bot`, deploy `dep-dbjckhrbc2fs73cegte0` **live** após configuração. `SUPABASE_AUTH_ENABLED=true`; chave **publicável** do projeto correto configurada sem exposição; `SUPABASE_AUTH_REDIRECT_BASE_URL=https://shopee-bot-fj0w.onrender.com`; `SUPABASE_LEGACY_SUPPORT_USERNAME=RafaelTesteCliente`; `SUPABASE_AUTH_EMAIL_SIGNUP_ENABLED=false` (sem SMTP próprio para público).
- **Smoke anônimo de produção:** `/login` 200, `/api/health/ready` 200, `/api/auth/supabase/config` 200 (`email_enabled=true`, `google_enabled=true`, `email_signup_enabled=false`, `legacy_support_enabled=true`), `/api/auth/supabase/google/authorize` 302; tentativa artificial com username inexistente no login legado retorna 410. Logs recentes sem novo erro de aplicação após deploy (somente SIGTERM normal do worker na troca).
- **Conta de suporte Shopee preservada:** `RafaelTesteCliente` continua USER, sem e-mail/Google, validada no backend Render contra hash existente em `public.users` Supabase; bypass legado **apenas** para esse username autorizado, com bcrypt/rate limit. Nenhuma senha, vínculo ou dado foi alterado; não remover nem excluir automaticamente.
- **Pendências explícitas:** Rafa precisa confirmar um **novo login Google completo em produção** até `rafastudio` ADMIN; o smoke 302 não prova callback/sessão real. Não foi usada senha verdadeira do suporte, portanto login E2E dele também não foi repetido. Recuperação de senha por link implementada, mas entrega real de e-mail não homologada. **Cadastro público por e-mail permanece desligado** até configuração/validação SMTP após domínio próprio. JWT interno de até 24h ainda é ponte transitória e requer plano futuro de revogação/migração.

## Decisão do proprietário — conta temporária da Shopee e retirada do login legado (01/11/2026)

**Vigente até nova ordem de Rafa.** `RafaelTesteCliente` (USER, ID `2e895580-b2ac-4254-83ce-f465e77918c1`) é uma conta de testes destinada à equipe de suporte da Shopee. **Mantê-la exatamente como está:** acesso por nome de usuário e senha legada, sem e-mail, sem Google, sem outro provedor OAuth, sem cadastro fictício no Supabase Auth e sem alteração de senha/permissões/dados. O hash da senha já está em `public.users` no Supabase; a API atualmente hospedada no Render apenas valida esse login. O Supabase Auth/GoTrue não oferece senha+username nativos sem email/telefone; não iniciar autenticação especial/Edge Function para esta conta.

**Gatilho futuro (não automático):** Rafa informa que a Shopee concluiu os testes e concedeu a aprovação necessária. **Só depois** ele decidirá/executará a exclusão de `RafaelTesteCliente` e autorizará, em tarefa separada, a retirada definitiva do fluxo de autenticação legado do backend no Render. Aprovação da Shopee, isoladamente, **não autoriza** nenhum agente a excluir conta, senha ou recursos.

**Checklist futuro obrigatório:**
1. Confirmar encerramento dos testes com Rafa; inventariar perfis, credenciais, posts, agendamentos, jobs, mídia, logs e obrigações de retenção da conta antes da exclusão.
2. Planejar backup/reversibilidade, revogar sessões ativas e executar a exclusão **somente mediante ordem explícita**, com conferência dos IDs exatos e dependências/FKs. Preservar auditoria legal necessária; não limpar tabelas indiscriminadamente.
3. Verificar que a conta não autentica mais nem detém recursos indevidos. Separadamente, garantir que login Google do ADMIN e todos os fluxos de email/recuperação/registro por Supabase estão testados em staging e prontos para produção.
4. Remover verificação de senha legada, endpoints e modos de login antigos, hashes e dependências **somente após migração integral das demais contas e sessões**, com PR → CI → staging → testes → PR main → deploy/monitoramento e plano de reversão. A hospedagem da API no Render é outra decisão: \"tirar Auth do Render\" significa retirar a **verificação de credenciais legadas**, não necessariamente remover o serviço Render.
5. Atualizar `AGENTS.md`, guia mestre, `docs/TASK.md` e espelhos no Vault, anotando consentimento, evidências, PR/commit e testes.

**Até esse gatilho:** não criar novo mecanismo de username-only, não forçar Supabase Auth nativo nesta conta, não desligar o único login que permite os testes da Shopee e não promover a migração de autenticação para produção se ela bloquear essa conta.

## Correção do retorno Google pós-mesclagem — PR #153, 01/11/2026

- [x] Causa identificada por logs reais e leitura do SHA staging `645c815`: Supabase `/token` e `/user` 200, Render callback 303; frontend `PanelPage` redirecionava para `/login` porque o Zustand `isAuthenticated=false`, **antes** de consultar o cookie recém-criado em `/auth/me`.
- [x] [PR #153](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/153) integrado a staging no merge `1613cb2`, CI #424 verde, Render `dep-dbjbsd2vcj2c73erdmag` **live**. `PanelPage` recupera usuário validado em `/auth/me` e reidrata Zustand antes de redirecionar.
- [x] Browser no SHA novo: cookie Google existente reidratou a sessão, carregou `/admin/overview`, nome `rafastudio` e papel `Administrador`. [ ] OAuth completo novo pós-deploy ainda pendente; confirmar recursos no site e logout.
- [x] DECIDIDO: `RafaelTesteCliente` permanece temporariamente no login legado usuário/senha validado pela API Render; senha hash já no Supabase. Sem e-mail/Google, sem Edge Function ou fluxo especial. Excluir apenas após conclusão/aprovação dos testes Shopee, solicitação de Rafa e revisão de dependências. Retirada definitiva do Auth legado fica para etapa posterior.

## Autenticação Google — primeiro vínculo manual concluído, 01/11/2026

- [x] Migração 066 registrada; PR #149 staging, Google Auth só em staging. Callback fixado no PR #152; CI #419 verde, deploy `645c815` live; /token e /user 200 em OAuth real.
- [x] Rafa concluiu onboarding Google `raffastudioproducoes@gmail.com`; navegador confirmou USER `Raffastudio` com sessão ativa, zero produtos/posts/listas; logout confirmado.
- [x] Sob autorização específica, operação SQL atômica transferiu o Auth UUID e e-mail ao ADMIN legado `rafastudio`, mantendo ID, perfil, 6 produtos, 6 posts, 4 listas, credenciais e função ADMIN. Origem USER provisória retida para auditoria, sem associação Auth. Ver `docs/SUPABASE-AUTH-MIGRACAO.md`.
- [ ] **Homologar segundo login pós-mesclagem:** a solicitação de login no navegador foi recusada; retestar quando o proprietário solicitar, confirmar dashboard ADMIN e recursos antigos. Não alegar E2E concluído.
- [x] Decisão do proprietário: `RafaelTesteCliente` não terá Gmail nem qualquer e-mail por enquanto; conta destinada a suporte Shopee com usuário/senha. **Nenhuma segunda mesclagem autorizada.**
- [ ] Homologar entrega real de e-mails/recovery e migração/revogação das sessões JWT transitórias. Supabase Auth já está **ativo em produção** para Google e e-mail; cadastro público por e-mail está desabilitado até SMTP próprio.

## Correção de publicações interrompidas por deploy — fechamento 31/10/2026

- [x] **Causa confirmada:** Threads #23 e #27 iniciados durante deploys Render; workers antigos encerrados 2s/4s depois. Supabase registrou lease expirado, sem ID externo.
- [x] **Proteção do encerramento:** `PublishingGeventWorker` recebe SIGTERM, impede novos disparos e aguarda jobs em voo dentro do limite do Render. PR [#127](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/127).
- [x] **Recuperação segura e prevenção de duplicação:** migrações aditivas 060/061, `external_started_at` antes do primeiro POST/upload, `preflight_claim_token` ligado ao lease da versão nova e `idempotency_key`. Retoma somente pré-envio; `unknown` permanece sem retry. PR [#128](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/128).
- [x] **Testes de reinício e concorrência:** novos testes mockados de SIGTERM, claim perdido, fronteira de envio, worker legado, status incerto e recovery. CI final de staging [41242800604](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41242800604) e CI PR main [41242969664](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41242969664) aprovados.
- [x] **Staging:** commit `20fc710`, deploy `dep-dbj5l8mq1p3s73ae5feg` live; smoke HTTP [41242800586](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41242800586) e ZAP passivo [41242800631](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41242800631) aprovados. Migrações 060/061 confirmadas no Supabase compartilhado.
- [x] **Produção:** PR [#129](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/129), `main` `86a23ff`, deploy `dep-dbj5mvlg1s2s73fl9110` live, CI [41243084679](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41243084679) aprovado; `/health` e `/api/health/ready` HTTP 200. Comparação entre branches retornou `files=[]`.
- [x] **Preservação dos dados:** os dois jobs antigos permanecem `unknown`; nenhuma publicação real ou alteração de credenciais feita neste lote.
- [ ] **Validação externa real:** confirmar uma publicação de teste autorizada no Threads e reconciliação, sem usar os dois posts antigos. Testes mockados não garantem resposta do provedor sob queda de rede.
- [ ] **Limite estrutural conhecido:** Render Free pode suspender o processo por inatividade e o SIGKILL após o prazo de shutdown não é evitável pela aplicação. Reavaliar opção gratuita de acionamento confiável antes de prometer entrega 24/7 sem tráfego.


# TASK — Shopee Auto Vendas

## Analise de redes — fase 1 em staging (2026-10-21)

- [x] Matriz de APIs, metricas e permissoes documentada em `docs/ANALISE-REDES-PLANO.md`.
- [x] Pagina e endpoint de resultados operacionais por rede/perfil e periodo, sem fingir insights ausentes.
- [x] Commit `2f091f7` e registro `c3de85e` publicados em staging; deploy Render e acesso sem sessao (401) validados.
- [ ] Executar sondas autenticadas com a conta de teste e validar isolamento com duas contas e dois perfis. Conexao verde de identidade nao prova acesso a insights.
- [ ] Fases 2-5: autorizacoes e coleta oficial por rede, snapshots, tendencias, comparacoes e atribuicao de cliques/conversoes (gates no plano).

## Entrega 2026-10-21 — versao 2.7.0

- [x] "Agora" sem etiqueta de agendamento; "Agendar" e recorrencia com ate cinco horarios por dia.
- [x] Coluna `posts.publish_immediately` confirmada no Supabase compartilhado em 2026-10-21.
- [x] MP4 reencodificado antes do Storage; 852 testes da API verdes com dependencias fixadas.
- [ ] Confirmar upload autenticado de video e publicacao real por rede no Render.
- [ ] Scanner antivirus e processamento isolado para video antes de afirmar seguranca contra malware; video permanece habilitado com risco documentado.

## Prioridade atual — 2026-10-16

1. Concluir e retestar o pentest (54 alertas por ID e achados manuais) antes
   do relatório final para a Shopee. Os lotes de dependências foram implantados
   em `staging`, com 827 testes da API passando localmente; ainda faltam
   inventário da imagem, reteste por ID e corrigir logout, CSRF e CSP restante.
2. Validar publicação, isolamento por perfil, recuperação da fila e o MVP em
   staging. Medir buscas e cache antes de escalar no Render/Supabase.
3. Somente depois do pentest e relatório, retomar Shopee Video, ainda condicionado
   à confirmação oficial de permissões e endpoint de publicação da Shopee.

> Fases e tarefas derivadas do PRD e do histórico real (`git log`, `docs/ROADMAP_MIGRACAO.md`,
> `docs/CHECKLIST_MIGRACAO.md`, vault Obsidian `00-INDICE-Estado-Atual.md`). Uma tarefa só é
> marcada **Concluída** com evidência de código ou teste passando; senão fica **Bloqueada** ou
> **Pendente**. Última verificação: 2026-10-11.

## Entrega 2026-10-15 — versão 2.6.0 (em `staging`)

- [x] Painel admin atualizado: globo de localização (somente demonstração), métricas de escala e capacidade, tendências, scrollbar temática.
- [x] Separação cliente/admin: ADMIN abre `/admin/overview`; "Ir para o site" e "Painel admin"; overrides manuais em `/admin/credentials/*`; `GET /credentials` sem `check_message`.
- [x] Métricas Render sempre do serviço de produção (`RENDER_ADMIN_SERVICE_ID`).
- [ ] Métricas de usuários (origem, analytics, presença) e coleta de localização: em breve.
- [ ] Rafa revisar e aplicar a migração 051 (`docs/migrations-pendentes/`).

## Entrega 2026-10-15 — versão 2.5.0 (em `staging`)

- [x] Esqueleto de carregamento global revisado, splash HTML e `OrbitalLoader`.
- [x] Painel administrativo isolado em `/admin` (guarda no frontend e no backend; sem IP de logs).
- [x] Segurança: replay de callbacks Meta/Threads, ownership de credenciais, CORS explícito, validação de mídia.
- [ ] Aplicar manualmente a migração 051 (`docs/migrations-pendentes/`) com autorização de Rafa.
- [ ] Promover `staging` para `main` (não feito).

## Entrega 2026-10-14 — versão 2.4.0

- [x] Identidade AUTO ORBITAL: paleta e grafites nos tokens, logos, favicon, PWA instalável (manifest e service worker), nome visível trocado. Layout e fonte Mona Sans preservados.
- [x] Páginas de Ajuda/FAQ e Termos/Política de Privacidade reescritas (âncora `#exclusao-de-dados`).
- [ ] Revisão jurídica dos textos de Termos e Privacidade.
- [x] Callbacks públicos Meta/Threads: desautorizar, exclusão de dados, status.
- [x] URLs de privacidade, termos e exclusão corrigidas no painel da Meta.
- [ ] App Meta em modo desenvolvimento: Threads com convite pendente para @rotadesconto; Facebook/Instagram precisam da conta de teste como Testador. Para clientes reais, publicar o app (verificação da empresa e análise do app).
- [x] X desativado até plano pago.
- [ ] TikTok foto: melhoria futura.

## Atualização 2026-10-12 — publicação de mídia e agendamento

Plano: `docs/superpowers/plans/2026-10-12-publicacao-midia-agendamento.md`. Tarefas 1 a 6
implementadas localmente em `staging` (sem push); Tarefa 7 parcial.

- [x] Capacidades reais (`delivered_modes`) no backend e no frontend; planejador só devolve
  modo entregue e não converte texto inválido em `text_only`.
- [x] Rascunhos de mídia duráveis (migração 046, bucket privado `post-media`, expiração 24 h,
  escopo por perfil).
- [x] `POST /posts/preview` e `POST /posts/batch` (criação parcial, `group_id` no servidor).
- [x] Recorrência de até 7 dias (migração 047; `day_of_week` legado preservado).
- [x] Publicadores: Threads, Facebook (foto/álbum/vídeo), Instagram (foto/carrossel/Reels) e X
  (foto única). Evidência: `tests/api` 536, `tests/scheduler` 75, node 10, build ok.
- [ ] Aplicar migrações 046 e 047 no Supabase de staging (ação humana autorizada).
- [ ] Validação humana em staging por rede e modo; registrar só o que for observado.
- [ ] X está desabilitado até virar plano pago; quando reabrir, validar `media.write` e reconectar
  a conta de teste se necessário.
- [ ] TikTok foto: Creator Info no fluxo do usuário e URL em domínio/prefixo verificado.
- [x] Graph API do Facebook/Instagram revisada para `v26.0`; ainda garantir ordem de mídia por contrato e
  `SUPABASE_URL`/`SUPABASE_KEY` no scheduler do staging.
- [x] Mudar `VERSION` para `2.3.0` e fazer o push final só depois de tudo validado.

## Atualização 2026-10-13 — mídia por rede em staging

- [x] Bandeja de fotos (`MediaTray`) para carrossel/álbum, com ordem escolhida pelo usuário.
- [x] Adaptação por rede (`adapt_media`, `dropped`): remove o que a rede não aceita em vez de
  bloquear; limites e resumo de mídia no seletor; máscaras de data/hora pt-BR.
- [x] Remoção das rotas Flask de posts (frontend usa só FastAPI).
- [x] Teste real em staging: Instagram e Threads ok; Facebook corrigido (mix imagem+vídeo).
- [ ] X: recarregar créditos da conta de desenvolvedor (402 `credits depleted`, externo).
- [ ] TikTok: Creator Info no fluxo do usuário + URL em domínio verificado (externo).

## Atualização 2026-10-11 — composição de mídia por rede

- [ ] Implementar planejador de compatibilidade por rede para foto única, carrossel e vídeo,
  reaproveitando arquivos sem misturar `user_id` ou `profile_id`. A especificação aprovada é
  `docs/superpowers/specs/2026-10-11-composicao-midia-por-rede-design.md`.
- [ ] Criar preview com abas de mídia somente quando houver composição diferente por rede e
  alertas prévios que informem formato, limite ou tamanho incompatível.
- [ ] Aplicar o fallback aprovado: rede com mídia incompatível publica somente o texto válido
  quando a API da rede suportar texto sem mídia; sem esse modo ou sem texto válido, ela fica fora
  sem cancelar as outras.
- [ ] Implementar e validar publicadores por modo compatível. Vídeo continua pendência separada
  até existir teste real aprovado para cada rede; Kwai segue fora por não ter API pública.

## Atualização 2026-10-10 — Isolamento obrigatório de credenciais e publicação

- [x] OAuth passa o `profile_id` assinado no `state` e rejeita callback concluído sob outro
  perfil. O app OAuth é global, mas o token emitido pertence exclusivamente ao usuário e
  perfil que iniciou a autorização.
- [x] Jobs de publicação e atualização de catálogo sem `profile_id` agora falham fechados;
  não escolhem credencial, post, produto nem token "por usuário" como compatibilidade.
- [x] Os cinco publicadores consultam post e produto pelo perfil do job. Renovação de token X
  e TikTok atualiza somente a linha do mesmo perfil.
- [x] O painel Flask legado de credenciais só é registrado quando
  `LEGACY_PANEL_ENABLED=true`; a superfície padrão é React/FastAPI escopada.
- [x] Evidência local: 20 testes do scheduler e 100 testes de OAuth/credenciais/posts verdes.
  Não há merge para `main` nesta tarefa; validação funcional no staging permanece necessária.

## Atualização 2026-10-10 — contrato do cliente e cobertura de mídia

- [x] Usuário comum conecta Threads, X, Facebook, Instagram e TikTok exclusivamente por OAuth,
  após aviso de consentimento da rede. Shopee e IA permanecem as exceções manuais.
- [x] Overrides manuais sociais e Kwai são ADMIN-only também na API; não dependem de campos
  escondidos no frontend como controle de segurança.
- [x] Caminho local de imagem: Threads, Facebook e Instagram enviam mídia por URL pública
  temporária. Falta validar publicação real no staging antes de declarar a cobertura concluída.
- [ ] X ainda precisa de upload de mídia e de acesso/crédito na API. TikTok Photo Direct Post
  requer URL em domínio/prefixo verificado e Creator Info renderizado no fluxo do usuário.
- [ ] Vídeo: manter como tarefa separada. Não declarar cobertura de vídeo a partir de testes com
  imagem.

## Fase 0-8.1 — Migração Flask → React + FastAPI

Todas concluídas (evidência: `docs/ROADMAP_MIGRACAO.md`, código presente e testado).

| Fase | Status | Evidência |
| --- | --- | --- |
| 0 — Estrutura (API stub, frontend stub) | Concluída | `api/`, `frontend/` existem e buildam |
| 1 — Auth (login/logout/sessão) | Concluída | `api/routers/auth.py`, cookie JWT httpOnly, guard em `PanelPage` |
| 2 — Painel/Dashboard | Concluída | `api/routers/dashboard.py`, `DashboardPage.tsx` |
| 3 — Produtos (CRUD) | Concluída | 13/13 testes verdes (`tests/api`) |
| 4 — Listas de produtos | Concluída | CRUD completo |
| 5 — Posts (thread, mídia, agendamento, copy IA) | Concluída, com simplificações | Upload de mídia só na head da thread (limitação conhecida, não bug) |
| 6 — Credenciais (7 redes, nunca reexibe valor) | Concluída | `api/routers/credentials.py` |
| 7 — Usuários (admin-only) | Concluída | `api/routers/users.py` |
| 8 — Scheduler: decisão + bridge interno | Concluída | ADR 19 (vault), `web/routes/internal.py` |
| 8.1 — Consolidação final (mesmo container, proxy, OAuth Threads na API nova) | Concluída no código | `Dockerfile`, `gunicorn.conf.py`, `web/routes/api_proxy.py` |

## Fase 9 — Migração de OAuth para app único (X, TikTok, Instagram, Facebook)

**Concluída no código.** Threads já nascera assim; X/TikTok/Instagram migraram do modelo
per-user para app único (`api/x_oauth.py`, `api/tiktok_oauth.py`, `api/instagram_oauth.py`,
env vars `X_CLIENT_ID/SECRET`, `TIKTOK_CLIENT_KEY/SECRET`, `INSTAGRAM_APP_ID/SECRET`);
Facebook migrou depois, de token de Página colado manualmente para OAuth reaproveitando o
app do Instagram (`api/facebook_oauth.py`). Evidência: `git log` (`89e542b`, `205f405`,
`0d5f0b0`), vault `27-Migracao-App-Unico-OAuth.md`.

## Validação em produção — pendente real

**Atualização 2026-10-09 — OAuth observado em staging/produção antes de corrigir código:**

- [ ] **Threads para usuário comum:** resolver no Meta/Threads o erro externo
  `error_code=1349245` (`The user has not accepted the invite to test the app`). A conta
  `rafastudio`/AMD conecta; usuário comum precisa aceitar convite de teste/role no app ou o
  app precisa sair do modo restrito/aprovar acesso público. Depois disso, retestar
  `Conectar Threads` no usuário normal.
- [x] **TikTok redirect URI:** corrigir no TikTok for Developers o erro de `redirect_uri`.
  Achado real em 2026-10-09: o Login Kit Live tinha só a URL de produção
  (`https://shopee-bot-fj0w.onrender.com/api/credentials/tiktok/callback`). Para testar
  staging, adicionar também
  `https://shopee-bot-staging.onrender.com/api/credentials/tiktok/callback` na aba Web do
  Login Kit, sem remover a produção. O arquivo de URL prefix pedido pelo TikTok para staging
  (`tiktoksuFLmrUFUxZQioEp5TCgDiOi0VAiY2e1.txt`) já foi servido no commit `12d1720`.
  **Resolvido:** Rafa testou no staging em 2026-10-09; a autorização funcionou e a conta
  ficou conectada.
- [x] **TikTok token expirado no staging:** resolvido por novo OAuth após corrigir o
  `redirect_uri`; não houve cópia manual de token do portal. A renovação automática do
  scheduler depende do `refresh_token` salvo por essa conexão bem-sucedida.
- [ ] **Teste de conexão com token do próprio usuário:** ainda validar X, Instagram e TikTok
  depois que houver tokens reais por usuário.

- [ ] **Validar no Render** que os dois processos (Flask + FastAPI) sobem corretamente no
  mesmo container e que `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` estão configurados lá.
  Só confirmado em dev local até a última verificação.
- [ ] **Cadastrar a callback URL de cada rede** (`.../api/credentials/{rede}/callback`) no
  painel de desenvolvedor correspondente (X Developer Portal, Meta for Developers, TikTok
  for Developers) — env var já configurada no Render, falta o app de cada plataforma
  reconhecer a URL como redirect válido.
  Callbacks por ambiente (`rede` = `threads`, `x`, `facebook`, `instagram`, `tiktok`):
  - **Staging:** `https://shopee-bot-staging.onrender.com/api/credentials/<rede>/callback`
  - **Produção:** `https://shopee-bot-fj0w.onrender.com/api/credentials/<rede>/callback`
  - TikTok: a aba Web do Login Kit Live precisa listar explicitamente produção e staging;
    `URL prefix`/arquivo `.txt` prova posse do prefixo, mas não substitui a Redirect URI.
- [ ] **Conectar de fato** X, Instagram, TikTok e validar Facebook/Threads em produção —
  ação humana (clicar "Conectar", autorizar), não pendência de código. Ver `docs/MEMORY.md`
  para o estado rede a rede.
- [ ] Aposentar rota legada `/credentials/threads/save?code=` do Flask — só depois de validar
  o novo fluxo (API nova) em produção.

## Redes sociais — status por tarefa

| Rede | Wrapper de publicação | Registrado no scheduler | OAuth de app único | Usuário conectado (token real) | Status |
| --- | --- | --- | --- | --- | --- |
| Threads | `scheduler/bot_post.py` | Sim | Sim | **Sim** | Publicação em produção não confirmada nesta verificação |
| X | `scheduler/bot_post_x.py` | Sim | Sim | Não | **Desabilitada** — em breve no plano pago; scheduler pula sem chamar a API |
| Instagram | `scheduler/bot_post_instagram.py` | Sim | Sim | Não | **Bloqueada** — idem |
| Facebook | `scheduler/bot_post_facebook.py` | Sim | Sim (migrado) | Não confirmado | **Bloqueada** — nunca validado com sucesso |
| TikTok | `scheduler/bot_post_tiktok.py` | Sim | Sim; domínio/prefixo e redirect staging validados | **Sim no staging** | Conexão/autorização confirmada em staging; publicação real ainda depende de teste/post e política Direct Post |
| Kwai | Não existe | — | — | — | **Bloqueada — sem API pública de postagem disponível** (decisão antiga, não é pendência nova) |

## Outras pendências reais (vault, 2026-09-28)

- [ ] `activities` está vazia em produção — sino de notificações funciona, mas não tem o que
  mostrar até um post publicar de fato.
- [ ] Revisão visual de Rafa nas telas React com dado real de produção.
- [ ] TikTok: recolar o Client Secret na tela de credenciais (o app_id foi limpo de espaço em
  branco, mas o secret é cifrado e não pôde ser inspecionado às cegas).

## Fora do backlog aprovado (visão, não sprint)

Garimpo inteligente por filtro, copywriter IA por persona configurável, canais adicionais
(Telegram/WhatsApp), dashboard de ROI real, multi-tenant com planos pagos — registrados em
`17-Visao-Expandida-Shopee-IA.md` (vault) como backlog pós-MVP, **não** aprovados como sprint
em execução.

## Fase 10 — Backlog de segurança/features (benchmarking MiauDelier Manager)

> Investigação de leitura em projeto irmão (MiauDelier Manager) levantou práticas de
> segurança e features maduras. Rafa decidiu incorporar como backlog/roadmap — **planejamento,
> não implementação**. Status atualizado após execução em 2026-09-30 (ver evidência por item).
> (origem: benchmarking MiauDelier Manager, 2026-09-29)

### Segurança

- [ ] **10.1 — RLS real no Supabase/Postgres.** **Decisão registrada, não é pendência de
  implementação:** todas as 22 tabelas do projeto já têm a policy `block_all_api`
  (deny-all via RLS), que é a defesa real aplicável aqui. RLS por `user_id`/`auth.uid()` não
  se aplica neste projeto porque o backend nunca autentica no Postgres como `anon`/
  `authenticated` — usa a `service_role` key direto, que ignora RLS sempre. Implementar
  policy por `user_id` seria código sem efeito nenhum. Decisão: não implementar, arquitetura
  já é segura pelo padrão existente. Reavaliar só se o backend passar a autenticar como
  `anon`/`authenticated`. (origem: benchmarking MiauDelier Manager, 2026-09-29; decisão:
  2026-09-30)
- [ ] **10.2 — Avaliar cifra de campo em repouso (envelope encryption).** **Decisão: não
  implementar agora.** Hoje não existe dado de negócio sensível no domínio do Shopee Auto
  Vendas além do que já é cifrado (senha via bcrypt, tokens OAuth via Fernet) — preço/produto
  são dados públicos da própria Shopee, não segredo do usuário. Reavaliar se o produto passar
  a guardar dado financeiro sensível próprio do usuário (ex.: custo de aquisição, margem
  real). (origem: benchmarking MiauDelier Manager, 2026-09-29; decisão: 2026-09-30)
- [x] **10.3 — Auditoria imutável de alterações sensíveis.** Concluída. Tabela `audit_events`
  (`database/migrations/034_create_audit_events_table.sql`, FK de `user_id` com
  `ON DELETE SET NULL` — corrigida após review de segurança para não quebrar a autoexclusão
  de conta de quem tem histórico de auditoria), lógica em `api/audit_trail.py`,
  instrumentação em products/lists/users, testes em `tests/api/test_audit_trail.py`.
  (origem: benchmarking MiauDelier Manager, 2026-09-29; concluída: 2026-09-30)
- [x] **10.4 — Sanitização de log contra vazamento de segredo.** Concluída.
  `api/utils/log_sanitizer.py` (regex de chaves sensíveis), aplicado em `audit_trail.py` e no
  backup/restore (10.8). (origem: benchmarking MiauDelier Manager, 2026-09-29; concluída:
  2026-09-30)
- [x] **10.5 — Endpoint de autoexclusão de conta e dados (LGPD/direito ao esquecimento).**
  Concluída. `DELETE /users/me` em `api/routers/users.py`, exige senha atual, rate limit
  próprio, testes em `tests/api/test_users.py`. (origem: benchmarking MiauDelier Manager,
  2026-09-29; concluída: 2026-09-30)
- [x] **10.6 — Rodar o Supabase Security Advisor** (linter de segurança nativo do Supabase)
  contra o projeto. Concluída. 0 achados de segurança; 19 índices de FK ausentes aplicados
  via `database/migrations/033_add_indexes_for_unindexed_foreign_keys.sql`. (origem:
  benchmarking MiauDelier Manager, 2026-09-29; concluída: 2026-09-30)
- [ ] **10.7 — Revisar rate limiting de login distribuído.** **Decisão: não migrar agora.**
  Render free tier = 1 instância = 1 worker; rate limit em memória de processo já é correto
  nesse cenário (a limitação documentada nos comentários `# ponytail:` do código só importa
  com múltiplos workers/instâncias). Migrar pra Redis exigiria provisionar infraestrutura
  paga nova — decisão de custo que não deve ser tomada sem o Rafa pedir explicitamente.
  Reavaliar se/quando escalar pra múltiplas instâncias. (origem: benchmarking MiauDelier
  Manager, 2026-09-29; decisão: 2026-09-30)

### Funcionalidades/Arquitetura

- [x] **10.8 — Backup/restore de dados do usuário com checksum de integridade.** Concluída.
  `GET/POST /users/me/backup` e `/restore` em `api/routers/users.py`, checksum
  HMAC-SHA256 (corrigido de SHA-256 puro após review de segurança), testes em
  `tests/api/test_users.py`. (origem: benchmarking MiauDelier Manager, 2026-09-29; concluída:
  2026-09-30)
- [x] **10.9 — Multi-perfil por conta.** Concluída. Limite de 3 perfis por conta (1 principal
  + 2 secundários; número confirmado por Rafa). Evidência: tabela `profiles` com backfill
  (migração 035) e `profile_id` aditivo em `products`/`product_lists` (migração 036) em
  `database/migrations/`; CRUD, ativação (reemite JWT com claim `profile_id`) e avatar
  (Supabase Storage, 5MB, magic-byte) em `api/routers/profiles.py`; página Perfis
  (`frontend/src/pages/ProfilesPage.tsx`, rota `/profiles`) e página `/settings` com troca de
  senha. **Escopo parcial de `profile_id`:** só produtos e listas; credenciais de redes, posts,
  mídias, activities, schedulers, audit_events e request_logs seguem só por `user_id` (rodada
  futura). Free/Plus/Premium é só rótulo, sem cobrança. (origem: benchmarking MiauDelier
  Manager, 2026-09-29; concluída: 2026-09-30)

- [x] **10.10 — Página "Ajuda & FAQ" com deep-link do tutorial Shopee.** Botão "?" no card
  Shopee de `CredentialsPage.tsx` leva direto pra aba "Tutorial Shopee" de uma nova página
  `HelpPage.tsx` (rota `/ajuda`, abas por `SegmentedToggle`, deep-link via `?tab=shopee`).
  Estrutura de abas pronta, conteúdo em placeholder ("Em breve") — texto e prints reais ficam
  para tarefa futura. Rodapé de suporte (e-mail, copiar, "Enviar mensagem", "Desenvolvido por
  Raffa Studio Produções") replicado estruturalmente do MiauDelier Manager
  (`src/features/ajuda/AjudaSuportePage.tsx`). Link novo no menu lateral (`PanelPage.tsx`,
  ícone `help-circle`). Concluída. (origem: pedido direto de Rafa, 2026-09-29)

- [x] **10.11 — Pesquisa Avançada de catálogo Shopee.** Concluída. Aba nova em
  `frontend/src/pages/ProductsPage.tsx` ("Meus Produtos"/"Pesquisa Avançada"), busca real via
  API de afiliados da Shopee (`api/shopee_catalog.py`, `api/routers/catalog.py`:
  `GET /products/catalog-search`, `GET /products/catalog-categories`), filtros (ordenação
  real da API, categoria), paginação client-side, botão para importar resultado pro catálogo
  pessoal (`POST /products` já existente). Campos de vendedor/rating/vendas são best-effort
  (schema real da Shopee não confirmado, fallback automático pro conjunto mínimo garantido).
  Filtro "mais recentes" não existe (API não suporta, confirmado com o Rafa). (origem: pedido
  direto de Rafa, 2026-09-30)
- [x] **10.12 — Polimento de acessibilidade Button/IconButton.** Concluída. Área de toque
  mínima 44×44px, sombra sutil (`--shadow-card`/`--shadow-pressed`), prop `loading`, foco
  visível (`:focus-visible` com `--focus-ring`, reaproveitando regra global já existente),
  sem paleta/fonte nova. (origem: pedido direto de Rafa, 2026-09-30)

- [x] **10.9b — Multi-perfil: escopo completo (nota datada 2026-10-05).** Concluída no código da
  branch `chore/phase-12-integration` (ainda não mergeada em `main`). A ressalva de "escopo
  parcial" do item 10.9 deixa de valer: migração 038 adiciona `profile_id` a credenciais das 7
  redes, `credential_checks`, `posts`, `medias`, `schedulers`, `activities`, `request_logs` e
  `audit_events` (FK `ON DELETE SET NULL`); 039 relaxa UNIQUE; 040 adiciona índice único com
  coalesce para deduplicar NULLs; 037 impõe o limite de 3 perfis por trigger. Backend, backup/restore
  e bots do scheduler respeitam o perfil ativo; UI com editar/excluir/ativar e perfil ativo na TopBar.
  Também nesta branch: claim `pwv`, validação do `profile_id` do token, rate limit em criar
  perfil/backup/restore, Dockerfile não-root + `HEALTHCHECK`, gunicorn com timeout e supervisão,
  CI/CD endurecidos. (origem: branch de integração, 2026-10-05)

- [x] **10.13 — Git Flow: pendências manuais.** `master` renomeada para `main` e branch
  `staging` criada. **Pendências manuais do Rafa (ação humana):** (a) proteção de branch
  indisponível — GitHub Free não oferece branch protection/Rulesets em repo privado (exige
  GitHub Pro ou repo público); (b) copiar as env vars da produção para o serviço
  `shopee-bot-staging` no Render; (c) ~~trocar o branch do serviço de produção no Render de
  `master` para `main`~~ — **concluído**: o serviço `shopee-bot` já está na branch `main`
  (verificado em 2026-10-06 via API do Render); (d) secret `RENDER_STAGING_DEPLOY_HOOK_URL` no GitHub, se quiser o
  workflow cd-staging. (origem: fluxo Git Flow, 2026-09-30)

  **Atualização 2026-10-05 — lista consolidada de pendências manuais de Rafa** (nenhuma é
  trabalho de código; conforme relatado pelo Rafa em 2026-10-05, os itens abaixo marcados
  com "confirmado" estão concluídos — decisão de não fazer branch protection agora e demais
  itens continuam pendentes):
  - [x] Env vars do serviço `shopee-bot-staging` no Render (copiar as de produção) — confirmado pelo Rafa, 2026-10-05.
  - [x] Trocar o branch de produção do serviço no Render de `master` para `main` — confirmado pelo Rafa, 2026-10-05.
  - [x] Secret `RENDER_STAGING_DEPLOY_HOOK_URL` no GitHub — confirmado pelo Rafa, 2026-10-05.
  - [x] Cadastrar as callback URLs de cada rede (X, Meta, TikTok) nos painéis de desenvolvedor — confirmado pelo Rafa, 2026-10-05.
  - [x] Conectar X, Instagram e TikTok (ação humana: clicar "Conectar" e autorizar) e recolar o Client Secret do TikTok — confirmado pelo Rafa, 2026-10-05.
  - [ ] Branch protection: exige GitHub Pro ou repositório público (GitHub Free não oferece em repo privado) — GitHub Pro ativo (confirmado pelo Rafa, 2026-10-05), mas branch protection ainda não configurada (possível agora, ainda não ativada).
  - [x] Aplicar as migrações 037, 038, 039, 040, 041 e 042 no Supabase — **concluído 2026-10-06**. Verificado via MCP: 6 migrações registradas em `public.migrations`; nenhum `profile_id` NULL em `posts`/`shopee_credentials` após backfill. Ver `docs/RULES.md` item 11 para procedimento + risco conhecido.
  - [ ] Merge de `staging` em `main` — preparado localmente em 2026-10-09 na branch
    `promote/staging-to-main-2026-10-09`, com a árvore final idêntica a `origin/staging`.
    Ainda não publicado em `main` nesta nota; antes do push, Rafa pediu cautela para não
    sobrescrever a versão online que está funcionando.

  **Fila pós-promoção acompanhada em 2026-10-09**:
  - [ ] TikTok: renovar token do usuário pelo fluxo OAuth ("Credenciais > TikTok > Conectar")
    quando o token atual estiver expirado; Client key/secret continuam sendo segredo de app,
    não token de usuário.
  - [ ] Teste de conexão por token do usuário para X, Instagram e TikTok — código em
    `staging`, pendente de validação real com credenciais conectadas.
  - [ ] Criador multi-rede com validação por rede, horário específico e mídia reutilizada —
    código em `staging`, pendente de teste manual ponta a ponta.
  - [ ] Hardening de segurança — código e testes em `staging`; validação local ficou
    bloqueada porque o ambiente mínimo não possui variáveis de banco para o `conftest.py`
    executar migrações (`host=None`).
  - [ ] Deploy automático de staging — arquivo `cd-staging.yml` em `staging`; aguardar decisão
    de Rafa antes de promover/ativar mudanças novas de deploy.

## Migração conta, perfis e papéis — 2026-10-11

- [x] Preparar migração 045 para consolidar credencial Shopee, IA e catálogo por `user_id`, com
  preflight que interrompe em caso de divergência.
- [x] Fazer serviços, rotas, listas, posts e restore respeitarem recursos compartilhados por
  conta e operação isolada por `user_id` + `profile_id`.
- [x] Separar módulos de ADMIN do frontend, com revalidação do papel no bootstrap e autorização
  mantida no backend.
- [x] Mover overrides manuais de redes para chunk ADMIN; USER usa OAuth para redes e formulários
  próprios apenas para Shopee e IA.
- [x] Regressão local: 511 testes da API passaram; build do frontend passou com chunks separados
  de Usuários, Logs e overrides.
- [x] Fechamento técnico: versão do produto elevada de `2.0.0` para `2.1.0` após as seis etapas
  anteriores; envio para `staging` e acompanhamento do deploy seguem esta tarefa.
- [ ] Aplicar a migração 045 no Supabase de staging durante o deploy e validar manualmente:
  três perfis, catálogo/IA/Shopee compartilhados e redes/listas/posts isolados.
- [ ] Validar o scheduler contra PostgreSQL configurado. O ambiente local não possui a conexão
  de teste; nenhum segredo foi lido nem reproduzido.
- [ ] Depois de todas as validações em staging, promover para `main` somente com aprovação
  explícita do responsável.

Ver também `docs/RULES.md` item 8 (padrão de migração de esquema de auth sem quebrar conta
existente — diretriz, não tarefa isolada).

## Escalabilidade — execução iniciada em 2026-10-16

- [x] **Scheduler/worker — preparação inicial.** Migração
  `052_create_publication_claims.sql`, lease atômico por publicação e atualização das agendas
  persistidas no boot. `SCHEDULER_ENABLED=true` preserva o modo atual; a futura instância web
  usará `false` e apontará `FLASK_INTERNAL_URL` ao worker. Evidência: CI e deploy da `main`
  verdes em 2026-10-16.
- [x] **Fila e idempotência local.** Código enviado a `staging` em `330137f`:
  migração `053_create_publish_jobs.sql`, chave única por ocorrência, claim com
  `SKIP LOCKED`, lease vencido como `unknown` e `external_id` quando a rede confirma.
  Erro ambíguo não recebe retry automático. O Render implantou `330137f` por
  auto deploy, aplicou a migração `053` e depois implantou `bc0eb92`; o health
  de staging respondeu `200`. O workflow `38978920492` pulou apenas o hook
  opcional. Promovido a `main` em `efba7a4`: CI `38979682487` verde, auto deploy
  Render `dep-db9as82vcj2c7395m750` live e `/health` 200. Pendente:
  reconciliação por provedor antes de retry de `unknown` e teste real de
  publicação com credenciais do usuário.
- [ ] **Banco e consultas.** Medir com `EXPLAIN (ANALYZE, BUFFERS)` em staging representativo;
  criar índices somente com evidência.
- [ ] **Hospedagem e réplicas.** Separar API/worker, carga em staging, borda Cloudflare e ativação
  gradual somente após os gates anteriores.

## FUTURO - Rebranding Auto Orbital

Decisão aprovada em 2026-10-13: a marca do produto é **Auto Orbital**. Implementação parcial entregue em 2026-10-14 (versão 2.4.0). Ver `docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md`.

- [ ] Fase A - Baseline.
- [x] Fase B - Brand Tokens (2.4.0).
- [ ] Fase C - Foundation.
- [x] Fase D - Brand Assets: logos, favicon, manifest e service worker (2.4.0).
- [ ] Fase E - App Shell. Feito em 2.4.0: login, rail e textos visíveis; falta migrar as telas em grupos.
- [ ] Fase F - Core Screens: dashboard, products, posts, lists.
- [ ] Fase G - Support Screens: credentials, profiles, settings, notifications, modals.
- [ ] Fase H - Brand Text. Feito em 2.4.0: textos visíveis; falta auditoria final do nome antigo.
- [ ] Fase I - Internal Renaming somente se aprovado.
- [ ] Fase J - QA Visual desktop/tablet/mobile/a11y.
- [ ] Fase K - Testes: typecheck/lint/build/tests.
- [ ] Fase L - Auditoria Final: nome antigo, hardcoded colors, assets, metadata e compatibilidade.
- Pendente (decisão do usuário): renome de identificadores internos (Fase I).

## FUTURO (em breve) — Carregamento em esqueleto (skeleton loading) das telas

Pedido do Rafa (2026-10-13, confirmado): trocar as barras/anéis de loading (spinners) por carregamento em esqueleto, como YouTube, LinkedIn, Facebook e Instagram.

Comportamento esperado:
- Enquanto os dados chegam, a tela já mostra a estrutura final com blocos cinza onde ficarão título, cards, linhas de tabela, imagens e textos, com tamanho e posição idênticos ao conteúdo real e um shimmer suave por cima.
- Quando os dados chegam, o conteúdo substitui os blocos no mesmo lugar, sem piscar e sem layout shift.
- Objetivo: a tela parecer já pronta e mais rápida, em vez de vazia com algo girando.

Escopo sugerido: criar UM componente único de esqueleto (variantes: texto, card, linha de tabela, avatar/imagem, KPI) usando os tokens/superfícies do Design System atual (no futuro Auto Orbital: grafites e gradiente orbital, sem exagero); aplicar nas telas de maior espera: dashboard (cards de números), produtos, listas, posts (histórico), credenciais (cartões das redes) e perfis. Spinner permanece apenas em botões de ação (Salvar, Publicar). Respeitar prefers-reduced-motion (sem shimmer, só bloco estático), aria-busy/aria-live adequados e contraste.

Dependências/encaixe: aproveitar a fase do rebranding em que as telas são migradas (fases E a G do docs/rebranding/34-Rebranding-Auto-Orbital-Plano-Mestre.md) e o item B4 da auditoria de UX; hoje o frontend NÃO tem nenhum componente de esqueleto (usa spinners em ~14 arquivos).

Critérios de aceite: sem layout shift (CLS ~0) na troca esqueleto→conteúdo; esqueleto com a mesma geometria do conteúdo real; build, typecheck e testes passando; verificação desktop e mobile; sem regressão de acessibilidade.

Status: não iniciado.

## 01/11/2026 — Autenticação Supabase e recuperação por e-mail (PR #149, rascunho)

- [x] **Código preparado no PR #149:** cadastro com nome de usuário, e-mail, duas senhas iguais e aceite dos Termos; login por e-mail/Google dependente da flag; confirmação via Supabase antes de liberar acesso.
- [x] **Código preparado no PR #149:** modal "Esqueci minha senha" solicita apenas e-mail; Supabase Auth envia link de recuperação; `/login` abre modal com duas senhas e aviso; Configurações deixa de editar senha local quando a flag estiver ativa.
- [x] **Testes unitários mockados versionados:** falhas de token, senhas diferentes, envio, atualização exclusiva pelo GoTrue e bloqueio de troca local (CI GitHub Actions #415, run 41269584721, `success`; 1004 testes API, 117 scheduler, 4 SQL e 25 web; build React aprovado no SHA `473e450`).
- [ ] **Homologação real:** aplicar migration 066 de forma controlada, testar cadastro confirmado, login e recuperação com o **e-mail de um membro autorizado** no SMTP padrão; testar link expirado, navegador diferente e Google.
- [ ] **Segurança:** finalizar sessões Supabase, revogação de JWTs locais na recuperação e preservação das contas legadas.
- [ ] **Envio externo:** habilitar somente quando houver SMTP próprio autorizado após domínio, conforme a tarefa permanente do Vault; não prometer cadastro aberto ao público com SMTP padrão.
- [x] **Promoção controlada de 01/11/2026:** Supabase Auth ativo em produção, com exceção restrita que **preserva** login de `RafaelTesteCliente`. CI #437 e smoke público registrados no topo. [ ] Concluir E2E Google real e migração de sessões; só após exclusão explicitamente autorizada planejar corte do legado.

## Referências

- `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`
- Vault: `00-INDICE-Estado-Atual.md`, `27-Migracao-App-Unico-OAuth.md`,
  `28-Historico-de-Requisicoes.md`
- `git log --oneline` (histórico completo)


## 31/10/2026 — Reenvio consciente de posts Threads sem confirmação

- [x] **Modal:** opção de post não encontrado no Threads, aviso de duplicação,
  confirmação explícita, estado "Reenvio na fila" e design system preservado.
  Testado no build React de PR #132, CI `41244475449`.
- [x] **Backend/fila:** `POST /posts/{id}/retry-unknown` valida dono, perfil,
  rede, mídia, ocorrência exata e concordância; RPC transacional migração 062
  enfileira tentativa única e mantém o `unknown` antigo. Testes Python aprovados.
- [x] **Supabase:** função `SECURITY INVOKER`, EXECUTE de `service_role`
  habilitado e anon/authenticated negados; chamada com IDs inexistentes devolveu
  NULL sem escrever. Dois unknown originais e zero reenvios manuais permanecem.
- [x] **Homologação:** PR #132, staging `b3492d3`, deploy
  `dep-dbj60civcj2c73elnv90` live, CI `41244645656` e
  smoke/ZAP `41244645690`/`41244645736` success;
  `/health` e `/api/health/ready` HTTP 200.
- [x] **Promoção:** PR #133 integrado à main `39026ad`; Render
  `dep-dbj62cu417fc73ajp880` live; `/health` e
  `/api/health/ready` HTTP 200 nos dois ambientes;
  branches sem diferenças de arquivos. CI main `41244974927` aprovado.
- [ ] **Validação real opcional:** reenvio externo somente se o titular verificar
  pessoalmente a ausência e acionar o botão; nenhuma publicação feita em teste.

### F4E-2B1 — contrato inerte de dispatch (PR #233; PRE-DEPLOY)

Contrato isolado e ainda não integrado ao executor: `CampaignDispatchIdentity` valida somente formato em memória; não comprova vínculo, posse ou imutabilidade persistida. `require_campaign_dispatch_authorization` sempre recusa, independentemente de flags. Não altera fluxo legado, não autoriza campanha e não protege o executor central de produção atual. Sem criação de jobs/posts/reservas, SQL, migrations, configuração ou chamadas externas. Antes de qualquer execução: identidade verificável e protegida entre reserva, ocorrência, job e post; guardas transacionais no claim e imediatamente antes da chamada externa; compatibilidade nos dois ambientes; proteção de mídia e revisão do acesso service_role. CI/revisão/deploy não confirmados neste registro. `VERSION=3.0.0`.
