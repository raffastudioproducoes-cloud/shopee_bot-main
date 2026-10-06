# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

> Branch `chore/phase-12-integration`. A versão (`VERSION`) só sobe no merge para `main`.
> Migrações exigidas: 037, 038 e 039 (aplicar no Supabase antes do deploy, ver `docs/RULES.md` item 11).

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
- CI: flake8 bloqueante para erros graves, Python 3.13, cache de pip/npm e `concurrency`.
- CD: dispara via `workflow_run` somente após CI verde em `main`; `curl -f`; `concurrency`.
- `gunicorn.conf.py`: `timeout = 120` e supervisão do subprocesso uvicorn (reinício com backoff).
- `Dockerfile` roda como usuário não-root.
- `.env-example` lista as variáveis realmente lidas pelo código e corrige X/TikTok (app único da
  plataforma, não por usuário). Documentação (`README`, `docs/`) atualizada.

### Fixed
- Troca de senha invalida JWTs antigos (claim `pwv`); tokens sem o claim continuam aceitos.
- `profile_id` do token é validado contra o dono; se inválido, cai no perfil principal.
- Registro provisiona o perfil principal com rollback do usuário órfão em caso de falha; admin que
  cria usuário também cria o perfil principal.
- Rate limit em criar perfil, backup e restore.
- `generate-copy` não devolve a exceção ao cliente; log de debug de páginas do Facebook removido.

### Notes (limitações conhecidas / pendências manuais)
- Pendências manuais de Rafa (não são código): env vars do serviço `shopee-bot-staging` no Render,
  trocar o branch de produção no Render de `master` para `main`, branch protection (exige GitHub Pro
  ou repo público), secret `RENDER_STAGING_DEPLOY_HOOK_URL`, callback URLs das redes, conectar
  X/Instagram/TikTok, recolar o Client Secret do TikTok, aplicar as migrações 037/038/039 no
  Supabase e conferir disco/permissão do container não-root, merge dos PRs.
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
