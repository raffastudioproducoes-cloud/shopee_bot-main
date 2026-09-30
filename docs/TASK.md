# TASK — Shopee Auto Vendas

> Fases e tarefas derivadas do PRD e do histórico real (`git log`, `docs/ROADMAP_MIGRACAO.md`,
> `docs/CHECKLIST_MIGRACAO.md`, vault Obsidian `00-INDICE-Estado-Atual.md`). Uma tarefa só é
> marcada **Concluída** com evidência de código ou teste passando; senão fica **Bloqueada** ou
> **Pendente**. Última verificação: 2026-09-29.

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

- [ ] **Validar no Render** que os dois processos (Flask + FastAPI) sobem corretamente no
  mesmo container e que `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` estão configurados lá.
  Só confirmado em dev local até a última verificação.
- [ ] **Cadastrar a callback URL de cada rede** (`.../api/credentials/{rede}/callback`) no
  painel de desenvolvedor correspondente (X Developer Portal, Meta for Developers, TikTok
  for Developers) — env var já configurada no Render, falta o app de cada plataforma
  reconhecer a URL como redirect válido.
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
| TikTok | `scheduler/bot_post_tiktok.py` | Sim | Sim; domínio verificado no painel | Não | **Bloqueada** — usuário + possível aprovação de parceiro (Direct Post) pendente |
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
> não implementação**. Todos os itens abaixo: status **Não iniciada**.
> (origem: benchmarking MiauDelier Manager, 2026-09-29)

### Segurança

- [ ] **10.1 — RLS real no Supabase/Postgres.** Habilitar Row Level Security nas tabelas
  sensíveis (`products`, `posts`, `product_lists`, `credentials`, `users`) com policy por
  `user_id`. Hoje o isolamento é só na lógica da aplicação (service-role direto via
  psycopg/supabase-py). Referência: MiauDelier Manager já usa RLS real em todas as tabelas.
  (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.2 — Avaliar cifra de campo em repouso (envelope encryption).** Chave derivada de
  senha embrulha uma chave de dados, para dados de negócio sensíveis além do que já é cifrado
  hoje (tokens OAuth via Fernet). Avaliar se faz sentido pro domínio do Shopee Auto Vendas.
  (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.3 — Auditoria imutável de alterações sensíveis.** Tabela de eventos (entidade,
  entidade_id, quem, quando, ação, valor_anterior, valor_novo) para mudanças de preço/exclusão/
  dado sensível. Hoje só existe `activities` para eventos de post/bot, não para auditoria de
  alteração de dado. (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.4 — Sanitização de log contra vazamento de segredo.** Revisar se logs do Shopee
  (uvicorn/`logger.exception` em `api/`) podem vazar senha/token/JWT acidentalmente; adicionar
  sanitização automática (regex de chaves sensíveis) antes de persistir/exibir logs, se
  aplicável. (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.5 — Endpoint de autoexclusão de conta e dados (LGPD/direito ao esquecimento).**
  Hoje só admin consegue deletar usuário via `DELETE /users/{id}`; avaliar RPC ou endpoint
  próprio para o próprio usuário solicitar exclusão de conta e dados.
  (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.6 — Rodar o Supabase Security Advisor** (linter de segurança nativo do Supabase)
  contra o projeto e corrigir os warnings reais encontrados (prática confirmada no MiauDelier:
  correção de `anon_security_definer_function_executable`).
  (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.7 — Revisar rate limiting de login distribuído.** Avaliar migrar de "em memória de
  processo" (dívida técnica já documentada) para solução distribuída (Redis/slowapi) antes de
  escalar para múltiplos workers/instâncias no Render.
  (origem: benchmarking MiauDelier Manager, 2026-09-29)

### Funcionalidades/Arquitetura

- [ ] **10.8 — Backup/restore de dados do usuário com checksum de integridade.** Exportar
  JSON com checksum, validar na importação, rejeitar arquivo corrompido. Avaliar se faz
  sentido pro Shopee Auto Vendas (ex.: exportar produtos/listas/posts do usuário).
  (origem: benchmarking MiauDelier Manager, 2026-09-29)
- [ ] **10.9 — Multi-perfil por conta.** Permitir que um usuário gerencie mais de uma
  loja/conta Shopee/Kwai sob o mesmo login, limitado a um número pequeno de perfis (bem menor
  que os 10 do MiauDelier — usar 3 como valor de partida; **número exato a confirmar com Rafa
  antes de implementar**). Avaliar impacto no schema atual (hoje é 1 conta = 1 usuário).
  (origem: benchmarking MiauDelier Manager, 2026-09-29)

Ver também `docs/RULES.md` item 8 (padrão de migração de esquema de auth sem quebrar conta
existente — diretriz, não tarefa isolada).

## Referências

- `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`
- Vault: `00-INDICE-Estado-Atual.md`, `27-Migracao-App-Unico-OAuth.md`,
  `28-Historico-de-Requisicoes.md`
- `git log --oneline` (histórico completo)
