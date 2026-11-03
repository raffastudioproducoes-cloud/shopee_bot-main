# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Added — F4B: catálogo persistente de quotas e consumo atômico (staging)
- Matriz Free/Pro/Premium confirmada; Pro suporta **2** campanhas ativas por perfil, Premium **5**, e postagem em cada rede conta individualmente.
- Migração aditiva 072 introduz plano canônico por conta, tabela auditável de limites e RPCs atômicas de criação de produtos/listas, sem trigger comercial global no Supabase compartilhado.
- API staging aplica 100/500/2.000 produtos por conta e 20/20/100 listas por perfil com isenção comercial de ADMIN. Postagens imediatas/recorrentes, ativação de campanhas e criação de perfis seguem para a F4C; nenhuma publicação real é disparada por esta alteração.

### Changed — F4A: identificação visual de planos (staging)
- Matriz Free/Pro/Premium, exceção ADMIN e fases de cotas registradas em `docs/PLANOS-F4-POLITICAS-E-FASES-20261103.md`, sem prometer restrições ainda não aplicadas ao backend.
- Cards de perfis passam a tratar `plus` legado como rótulo `Pro`, aceitam `pro` futuro e exibem `Administrador` se papel de ADMIN já estiver confirmado pela sessão. Migração, faturamento e regras de postagem continuam intocados neste incremento.
- Conta de teste `RafaelTesteCliente` recebeu etiqueta `premium` no perfil principal via operação controlada no Supabase, confirmada por releitura; conta ADMIN não sofreu alteração de banco.


### Added — F3C: postagens por dia e exclusão de rascunhos (PR #211, integrada em staging)
- Campanha por lista agora usa seletor de **1 a 15 postagens por dia**, com horários uniformemente distribuídos entre início e fim dos dias selecionados. Uma postagem usa o início da janela; janela pequena para múltiplas postagens é rejeitada.
- Rascunhos históricos com `interval_minutes` são convertidos ao carregar para `posts_per_day` (respeitando teto de 15 e exigindo revisão da prévia); nenhuma migração SQL necessária, pois o campo `schedule` é JSONB.
- Botão **Excluir** na lista de rascunhos, com confirmação inline na página; endpoint próprio protegido por usuário, perfil e revisão. Arquivos privados de campanha são removidos **antes** da exclusão da linha; falhas bloqueiam a operação, sem tocar em produtos, posts ou jobs.
- CI [#41581370451](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41581370451) verde, merge `140ea06`, Render `dep-dbkmmf7lk1mc73e1o2p0` LIVE e `/health` OK. Testes focados em planejamento, limites e exclusão segura; `main` e produção preservados. **Não habilita disparo/ativação nem altera planos por plataforma.**


### Added — F3B: nome da campanha e mídias persistentes por produto (PR #209, staging)
- Cada campanha recebe um nome próprio de até 120 caracteres, independentemente da lista usada; nomes distintos aparecem na recuperação de rascunhos.
- Preparação por produto permite anexar imagens/vídeos de PC/celular ao rascunho salvo, com até 10 arquivos de 50 MB, seleção da imagem principal Shopee preservada. Referências em tabela independente dos temporários que expiram em 24h.
- Bucket `post-media` permanece privado, com prefixo específico, sanitização de mídia existente, escopo usuário/perfil/produto, RLS/trigger e opção de excluir anexos. Migração `campaign_names_media_071` **aplicada com autorização** ao Supabase compartilhado em 03/11/2026, com RLS, grants e ownership verificados; PR #209 mesclada por squash somente em `staging` (`5ec24df`). Nenhuma ativação, post/job ou disparo.
- Layout do editor permanece integrado à página e responsivo. Regras técnicas em `docs/CAMPANHA-F3B-NOME-E-MIDIAS-20261103.md`.

- CI [#41578367282](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41578367282) aprovada; Render staging `dep-dbkm74ks728c738ritc0` LIVE, migration 071 reexecutada sem erro no boot, `/health` OK; nome e controles de anexos conferidos na UI autenticada. Nenhum arquivo de teste persistente nem publicação criada. `main` e versão `3.0.0` permanecem intocados.

### Fixed — F3A: reinício seguro após aplicação da 070
- PRs [#207](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/207) e [#208](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/208) mescladas em `staging`. O migrador reexecutava a 070 no boot e falhava no trigger já existente após a aplicação manual; guarda idempotente corrigiu e o deploy terminou LIVE com `/health` OK. Incidente documentado no Vault #61; `main` inalterada.


### Added — F3A: rascunhos de campanha persistidos (PR #207, mesclada staging)
- Nova API de rascunhos `/campaigns/drafts` para salvar, listar, consultar e revisar com controle por usuário/perfil e revisão otimista; preserva snapshots separados de título, texto, link, redes e foto Shopee por item.
- Página `Criar POST` com ações para salvar e recuperar rascunhos do servidor, mantendo a cópia local como proteção. A operação não cria posts, jobs, reservas de agenda ou publicações.
- Migration `070_campaign_drafts.sql` aditiva com RLS, integridade de dono/perfil/lista e índice; **aplicada com autorização de Rafa em 03/11/2026** ao Supabase compartilhado sob o nome `campaign_drafts_070`; inspeção confirmou RLS ativo, zero policies para acesso direto, `anon`/`authenticated` sem SELECT, `service_role` com SELECT/INSERT e trigger de ownership. Integração validada em staging após correção de inicialização na PR #208.
- Mídias próprias de campanha (fotos/vídeos enviados pelo usuário) exigem persistência durável separada antes da ativação. A publicação única mantém suas fontes e uploads existentes; não houve alteração nela.


### Added — preparação por produto da campanha (staging, sem ativação)
- Campanha por lista tem editor em página, por produto, para título, texto principal, texto específico por rede, link de afiliado, redes com credenciais válidas e opção de foto principal Shopee.
- Snapshots locais independentes por usuário/perfil/lista, sem modificar a lista-fonte; restauração preserva campos apagados, ordem e IDs permitidos. Prévia permanece somente leitura, sem gerar posts/jobs ou publicar.
- Contratos executáveis dos snapshots integrados ao gate frontend. Upload persistente de fotos/vídeos por item, IA em lote, persistência transacional e ativação serão entregas posteriores; publicação única e seus uploads estão intactos.

### Fixed — ícones de navegação e prévia (staging)
- Corrigido o menu **Criar POST**: o ícone Lucide `square-pen` já era solicitado pelo SideRail, mas não constava do registro central de `Icon`, resultando em espaço vazio. Corrigido também `calendar-search` no botão de prévia da campanha.
- Contrato automático de ícones da navegação e ação de prévia impede novas referências silenciosamente sem renderização. Sem alteração de rotas, permissões, dados ou publicação.

### Added — campanha por lista: prévia segura (PR #204, staging)
- Novo modo **Campanha por lista** na página `/posts/criar`, mantendo **Publicação única** e suas mídias/agenda anteriores sem regressão.
- Seleção de lista do perfil, ordenação local, até 30 dias inclusivos, dias/horários/intervalo, revezamento de um produto por horário e prévia de cobertura no fuso de Brasília.
- `POST /campaigns/preview` autenticado e somente leitura, com escopo de lista/produto e resposta sem ativação; rascunho local segregado. Não cria posts, jobs ou publicações. Registro: `docs/CAMPANHA-POR-LISTA-PREVIA-20261103.md`.

> **SemVer:** `VERSION=3.0.0` permanece a última versão publicada. Funcionalidades novas compatíveis de `[Não lançado]` são candidatas a **3.1.0** na próxima promoção **expressamente aprovada** de staging para main. Este registro não é uma release; não antecipar bump nem integrar `main` sem revisar o lote e obter aceite.


### Changed — página Criar POST sem aparência de modal (staging) e decisão R06
- Formulário de `/posts/criar` integrado ao layout do site: sem cartão central, com regiões de produto/mídia e texto/agendamento, duas colunas em desktop e fluxo fluido em tablet/celular. Prévia da criação passa a ser conteúdo da página, sem overlay em telas pequenas.
- Experimento de galeria extra Shopee **encerrado como indisponível na integração atual**: 3 sondagens autenticadas `productOfferV2` rejeitaram `imageUrls` e o link original real consultado exigiu login de comprador. Preservados imagem principal da Shopee e uploads locais de foto/vídeo.
- Sem alteração de APIs, worker, cron, tabelas, credenciais, publicação externa ou produção. Registro técnico: `docs/CRIAR-POST-LAYOUT-GALERIA-SHOPEE-20261103.md`.

### Added — Criar POST em página dedicada (staging, R01/R02 parcial)
- Menu lateral `Criar POST` e rota privada `/posts/criar`, transferindo compositor do modal para página responsiva; histórico permanece em `/posts`.
- Preservados criação imediata/recorrente, produto individual, foto principal Shopee, upload local de fotos/vídeos, IA, rascunhos, preview, validações e fluxo de dispatch/erros existente.
- Nenhuma API, agendamento, banco ou publicação externa modificada. Galeria adicional Shopee e edição de mídia futura permanecem pendentes de fonte oficial/versão segura.

### Added — edição futura de texto em staging (F1 isolada, sem enviar post)
- Revisões imutáveis de texto para ocorrências ainda não reivindicadas a mais de 30 minutos, preservando ID do post, agenda, foto Shopee, fotos/vídeos enviados e histórico. Seleção atômica de snapshot pela hora original no claim com suporte a retry seguro; endpoint de leitura separado do detalhe existente.
- Editor de texto sob demanda nos detalhes de posts agendados; rede, produto, mídia e horários não são alterados. RLS e banco seguem a migração 069 já aplicada e registrada; nenhuma publicação externa de teste.


### Added — teste isolado da galeria Shopee (somente staging; sem postagem)
- Endpoint autenticado e de leitura `GET /api/products/{id}/shopee-gallery-probe`, com `productOfferV2(itemId)`, teste condicional do campo `imageUrls`, fallback para `imageUrl`, filtragem de CDNs Shopee e escopo por conta. Usa apenas credenciais Shopee já cadastradas no backend; não modifica credenciais, agendamentos, uploads ou posts. Disponibilidade real de fotos adicionais depende de consulta autenticada em staging, sem assumir campo suportado.
- Testes mockados de erro de schema, rate limit, foto única, múltiplas fotos, segurança de URL e autenticação. Sem migração SQL e sem alteração de UI nesta PR.

### Added — piloto F0 no staging (gate desligado)
- Preparação aditiva da migração 068 e de escopos idempotentes para despacho central de agendas novas; antigas agendas de staging permanecem `legacy`. Reconciliador central só funciona com `ORBITAL_CENTRAL_DISPATCH_ENABLED=true` **em etapa futura**. Nesta implantação: flag desligada, nenhum job transferido, nenhum post de teste, sem mudança em main.
- Testes de criação/claim/rollback/espelhamento/cancelamento/`Agora` e expiração; detalhamento em [F0 — piloto no staging](docs/F0-CENTRAL-DISPATCH-STAGING-PILOT-20261102.md).


> Toda alteração integrada em `staging` deve ser registrada aqui por PR. `VERSION` é a fonte oficial da versão; nenhuma mudança passa para `main` sem classificação SemVer, changelog e validação. A próxima versão só é decidida na promoção aprovada.

## [3.0.0] - 2026-11-02

### Breaking Changes
- Novas publicações aceitam **um único produto**; composições com múltiplos produtos são rejeitadas no frontend e pela API. Registros anteriores são preservados.
- Foi removida a opção de **criar agendamento avulso ("Agendar")**. Novos posts utilizam `Agora` ou `Recorrente`; agendamentos históricos e o disparo interno de `Agora` não são apagados.

### Added
- Persistência local e isolada por conta/perfil de rascunhos de formulários, com recuperação após atualização ou fechamento e respeito a campos apagados intencionalmente; arquivos e segredos não são salvos.
- Geração de descrição por IA **individual por rede social**, com variantes editáveis, revisão dos limites de texto e hashtags e mensagens de compatibilidade de mídia.
- Identificador público `#ID` único e crescente para cada post, preservado em edições e não reutilizado após exclusão.
- Detalhamento de ocorrências recorrentes por dia/horário, status discreto e última publicação efetivamente confirmada.
- Entrada pública da landing e fluxos de autenticação Supabase Auth/Google, preservando o acesso legado controlado da conta de revisão Shopee.

### Changed
- Seletor de horários do desktop com controles de 24 horas e atalhos; experiência nativa Android mantida.
- Campo de upload de imagem/vídeo reposicionado imediatamente abaixo de "Usar fotos dos produtos Shopee".
- Mensagens de falha objetivas para USER; diagnóstico de API detalhado e recolhível restrito a ADMIN.
- Navegação, prévia e consulta dos posts reorganizadas sem permitir alteração de publicação já programada/tentada.

### Fixed
- Isolamento de identidade de usuário/perfil/post/agenda/ocorrência, inclusive para múltiplas publicações no mesmo segundo.
- Agrupamento de posts exclusivamente por `group_id` explícito, eliminando união indevida por texto ou horário.
- Preflight de indisponibilidade do scheduler antes de gravar post/mídia e preservação do rascunho na falha; separação de jobstores e fila por ambiente no código atual.
- Tratamento de retorno de postagem incerta, evitando apresentar envio não confirmado como sucesso ou repetir automaticamente uma publicação.

### Security
- Preservadas validações de dono/perfil, separação USER/ADMIN, sanitização das falhas da Meta e proteção de segredos e tokens.
- A conta `RafaelTesteCliente` continua reservada para a revisão Shopee, sem alteração de senha ou credenciais nesta atualização de versão.

### Verification and known limitations
- Código de funcionalidade já integrado à `main` pelos PRs #190/#192; documentação e configuração operacional devem ser verificadas por SHA/CI/Render, não inferidas a partir da versão.
- **Não houve novo teste de publicação real em redes sociais nesta atualização de metadados**; erro HTTP 403 Threads e permissões externas permanecem sob acompanhamento.
- O Supabase é compartilhado por `staging` e `main`. A implementação atual possui agendadores separados por ambiente; a decisão posterior de Rafa de **centralizar o despacho em produção** ainda exige adequação técnica independente, não incluída neste release documental.
- Referências: PRs #181, #184, #185, #186, #187, #189, #190, #191, #192 e #195.

## [2.7.0] - 2026-10-21

### Added
- Posts recorrentes podem ter ate cinco horarios por dia selecionado.
- Upload de MP4 e reencodificado antes de ser salvo no Storage, com limites de duracao, resolucao, tamanho, tempo e concorrencia.

### Fixed
- "Postar agora" e publicado imediatamente sem etiqueta de agendamento; "Agendar" conserva a data e a etiqueta apropriadas.
- Seletor de data/hora e estado do historico de posts alinhados ao tipo de publicacao.

### Security
- Video segue disponivel, mas o FFmpeg roda no container da API e nao ha scanner antivirus isolado. Nao declarar arquivos livres de malware; ver `docs/POST-MEDIA-SECURITY.md`.

### Verification
- Suite da API: 852 testes passaram com as versoes de dependencias fixadas no projeto. Deploy de `staging` do commit `ffbd470` confirmado live; upload autenticado de video no Render nao foi comprovado.

## Arquivo histórico — integração de multi-perfil (estado documentado em 2026-10-06)

> Registro histórico preservado; esta seção descreve a situação de sua época e não indica pendência atual da `main`.
>
> Branch `chore/phase-12-integration`. A versão (`VERSION`) só sobe no merge para `main`.
> Migrações exigidas: 037, 038, 039, 040, 041 e 042 (aplicar no Supabase antes do deploy, ver `docs/RULES.md` item 11).

### Added
- Multi-perfil completo: `profile_id` nas 14 tabelas restantes que tinham `user_id`
  (migração 038: credenciais das 7 redes, `credential_checks`, `posts`, `medias`, `schedulers`,
  `activities`, `request_logs`, `audit_events`), com `ON DELETE SET NULL`, índice e backfill para o
  perfil principal.
- Posts, mídias, credenciais das redes (leitura, escrita, OAuth, teste de conexão), dashboard,
  notificações, catálogo, logs/auditoria e backup/restore passam a respeitar o perfil ativo;
  scheduler e bots usam a credencial e as atividades do perfil do post (com fallback por `user_id`).
- Migração 037: trigger que impõe o limite de 3 perfis por conta no banco (atômico).
- UI de perfis: editar e excluir perfil, perfil ativo na TopBar, ativação sem recarregar a página;
  backup/restore sem `alert`/`confirm`.
- `GET /auth/me` devolve o `profile_id` ativo; o frontend lê o perfil ativo dali (sem `localStorage`).
- CI: job `frontend` (`npm ci` + `npm run build`), `.github/dependabot.yml` e
  `.github/pull_request_template.md`.
- `Dockerfile`: `HEALTHCHECK` em `/health`.
- `SECURITY.md` com contato e política de reporte.

### Changed
- Migração 039: removido o UNIQUE de `shopee_credentials.app_id` (mesma API Key em mais de um
  perfil) e o de `credential_checks` virou `(user_id, profile_id, network)`.
- Migração 040: índice único de `credential_checks` usa coalesce(profile_id, uuid('00000000-0000-0000-0000-000000000000'))
  para deduplicar NULLs em casos de fallback por `user_id`.
- Migração 041: `products` deixa de ser único por `(product_id, user_id)` e passa a `(user_id, product_id, coalesce(profile_id))`;
  o mesmo produto pode existir em 2 perfis. Restore cria/atualiza o produto do perfil ativo e `POST /products`
  duplicado no mesmo perfil devolve 409.
- CI: flake8 bloqueante para erros graves, Python 3.13, cache de pip/npm e `concurrency`.
- CD: dispara via `workflow_run` somente após CI verde em `main`; `curl -f`; `concurrency`.
- `gunicorn.conf.py`: `timeout = 120` e supervisão do subprocesso uvicorn (reinício com backoff).
- `Dockerfile` roda como usuário não-root.
- `.env-example` lista as variáveis realmente lidas pelo código e corrige X/TikTok (app único da
  plataforma, não por usuário). Documentação (`README`, `docs/`) atualizada.

### Fixed
- Troca de senha invalida JWTs antigos (claim `pwv`); tokens sem o claim continuam aceitos.
  Ativação de perfil (`POST /profiles/{id}/activate`) recalcula `pwv` no novo JWT.
- `profile_id` do token é validado contra o dono; se inválido, cai no perfil principal.
  Token sem claim `profile_id` defaults ao perfil principal, inclusive em `GET /auth/me`.
- `product_ids` de posts são validados por dono/perfil (400 Bad Request se inválido).
- Registro provisiona o perfil principal com rollback do usuário órfão em caso de falha; admin que
  cria usuário também cria o perfil principal.
- Rate limit em criar perfil, backup e restore.
- Supervisor uvicorn em `gunicorn.conf.py` (reinício com backoff em caso de crash) sem deixar processo órfão.
- `generate-copy` não devolve a exceção ao cliente; log de debug de páginas do Facebook removido.

### Notes (limitações conhecidas / pendências manuais — atualizado 2026-10-06)
- Pendências manuais de Rafa (não são código):
  - [CONCLUÍDO, 2026-10-05] Env vars do serviço `shopee-bot-staging` no Render.
  - [CONCLUÍDO, 2026-10-05] Trocar o branch de produção no Render de `master` para `main`.
  - [CONCLUÍDO, 2026-10-05] Secret `RENDER_STAGING_DEPLOY_HOOK_URL`.
  - [CONCLUÍDO, 2026-10-05] Callback URLs das redes (X, Meta, TikTok) nos painéis de desenvolvedor.
  - [CONCLUÍDO, 2026-10-05] Conectar X, Instagram e TikTok; recolar o Client Secret do TikTok.
  - [POSSÍVEL, NÃO ATIVADA] Branch protection (GitHub Pro ativo desde 2026-10-05, mas ainda não configurada).
  - [CONCLUÍDO, 2026-10-06] Aplicar as migrações 037/038/039/040/041/042 no Supabase — verificado via MCP: 6 migrações registradas em `public.migrations` (linhas); nenhum `profile_id` NULL em `posts`/`shopee_credentials` após backfill. Staging e produção compartilham MESMO banco. **Risco conhecido**: Código de produção antigo (sem este PR) usa upsert `on_conflict (product_id, user_id)` no restore; após migração 041 (que muda para `(user_id, product_id, coalesce(profile_id))`), o restore falhará com violação de constraint. Solução: Merge desta branch (PR #10) corrige o restore. Prevenção: Aplicar migrações antes do deploy do PR #10. Ver `docs/RULES.md` item 11 para detalhe.
  - Merge dos PRs da branch `chore/phase-12-integration` em `main`.
  - Teste real de upload no container não-root (verificação de disco/permissão).
- Correção de nota anterior (2026-10-05): a limitação "`profile_id` ainda NÃO cobre credenciais,
  posts…" da 2.0.0 deixa de valer nesta branch.

## [2.0.0] - 2026-09-30

### Added
- Sistema de perfis por conta, limitado a 3 (1 principal + 2 secundários): tabela
  `profiles` (migração 035, com backfill do perfil principal) e `profile_id` aditivo
  apenas em `products` e `product_lists` (migração 036).
- CRUD de perfis e ativação de perfil (`api/routers/profiles.py`); ativar reemite o JWT
  com o claim `profile_id`.
- Produtos e listas escopados pelo perfil ativo, compatível com token antigo (sem claim);
  endpoints por ID isolados entre perfis da mesma conta.
- Upload de avatar de perfil no Supabase Storage (bucket `avatars`), limite de 5MB e
  validação por magic-byte.
- Página "Perfis" (`/profiles`) com grid de cards (criar, ativar, enviar avatar).
- Página de Configurações (`/settings`) com troca de senha (`PUT /settings/password`,
  com rate limit).
- Branch `staging` criada e serviço `shopee-bot-staging` criado no Render (plano Free), MAS ainda sem env vars/deploy hook configurados — ver `docs/TASK.md` item 10.13 (pendências manuais).
- Fluxo Git Flow (`main`/`staging`/`feature/*`, SemVer só sobe no merge pra `main`; proteção automática de branch indisponível no plano Free do GitHub — ver `docs/TASK.md` 10.13).

### Changed
- Página "Usuários" renomeada para "Perfis" (rota `/profiles`); a seção admin de contas
  de login foi preservada na mesma página.
- Branch padrão do repositório renomeada de `master` para `main`; referências da CI
  atualizadas.

### Notes (limitações conhecidas)
- `profile_id` ainda NÃO cobre credenciais de redes, posts, mídias, activities,
  schedulers, audit_events e request_logs: continuam escopados só por `user_id`.
  Previsto para uma rodada futura.
- Avatar via OAuth Google/Apple está fora de escopo (o login do projeto é usuário/senha).
- Free/Plus/Premium é apenas rótulo; não há cobrança.
- Proteção automática de branch não está ativa (limitação do GitHub Free em repositório
  privado); o fluxo Git Flow depende de disciplina. Ver `docs/RULES.md` item 1.
