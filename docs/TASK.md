# TASK — Shopee Auto Vendas

> Fases e tarefas derivadas do PRD e do histórico real (`git log`, `docs/ROADMAP_MIGRACAO.md`,
> `docs/CHECKLIST_MIGRACAO.md`, vault Obsidian `00-INDICE-Estado-Atual.md`). Uma tarefa só é
> marcada **Concluída** com evidência de código ou teste passando; senão fica **Bloqueada** ou
> **Pendente**. Última verificação: 2026-10-11.

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
- [ ] Habilitar `media.write` no portal do X e reconectar a conta de teste; persistir o escopo
  concedido.
- [ ] TikTok foto: Creator Info no fluxo do usuário e URL em domínio/prefixo verificado.
- [ ] Revisar versão da API do Facebook (`v18.0`), garantir ordem de mídia por contrato e
  `SUPABASE_URL`/`SUPABASE_KEY` no scheduler do staging.
- [ ] Mudar `VERSION` para `2.2.0` e fazer o push final só depois de tudo validado.

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
| X | `scheduler/bot_post_x.py` | Sim | Sim | Não | **Bloqueada** — aguardando usuário concluir "Conectar" |
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
  - [ ] Merge dos PRs da branch `chore/phase-12-integration` em `main`.

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

## Referências

- `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`
- Vault: `00-INDICE-Estado-Atual.md`, `27-Migracao-App-Unico-OAuth.md`,
  `28-Historico-de-Requisicoes.md`
- `git log --oneline` (histórico completo)
