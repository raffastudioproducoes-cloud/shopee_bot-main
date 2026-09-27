# 00 — Índice / Estado Atual do Projeto

> Fonte viva de estado — ler antes de qualquer sessão nova (Claude Code ou humana).
> Atualizado em 2026-09-27 por uma sessão do Claude Code rodando na nuvem (sem acesso
> ao vault local do Obsidian — ver aviso abaixo).

## ⚠️ Aviso sobre este documento

Este arquivo foi criado **dentro do repositório** (`vault/`) a pedido do usuário, pra
consolidar documentação que estava (ou deveria estar) espalhada entre o vault local do
Obsidian (`C:\Users\rafae\Documents\Obsidian\J.A.R.V.I.S_Obsidian`) e os docs do próprio
projeto (`docs/`, `README.md`, `api/README.md`).

**Eu não tive acesso ao vault local** — a sessão que escreveu isto roda num container na
nuvem, isolado do sistema de arquivos do Windows do usuário. Os documentos abaixo,
citados pelo `README.md` da raiz, existem (ou existiam) só no vault local e **não pude
verificá-los nem atualizá-los de verdade**:

- `00-INDICE-Estado-Atual.md` (o antecessor deste arquivo, se existir)
- `26-Deploy-Render.md`
- `21-Relatorio-Correcoes-Seguranca-2026-08-21.md`
- `19-ADR-Scheduler-In-Process.md`

Pra reconciliar de verdade, ou (a) cole/anexe o conteúdo desses arquivos numa próxima
mensagem, ou (b) rode uma sessão do Claude Code **localmente** (no Windows, com acesso
tanto ao vault quanto a uma cópia do repo) pra fazer a fusão migrando o conteúdo real do
vault pra cá. Este documento cobre só o que dá pra inferir com certeza a partir do
próprio código e do que foi corrigido nesta sessão.

## O que este projeto é (resumo do README)

Painel que automatiza divulgação de link de afiliado Shopee: garimpa produto, gera copy
com IA (Gemini), agenda/publica, organiza em listas, guarda credenciais cifradas, loga
atividades. Dois frontends coexistindo durante a migração (Flask+Jinja2 em produção,
React novo em construção), duas APIs coexistindo (Flask legado + FastAPI novo), banco
Supabase (Postgres).

## Estado real por módulo (verificado nesta sessão, não só documentado)

| Módulo | Documentado (README/ROADMAP) | Verificado agora |
| --- | --- | --- |
| Auth (login/cookie) | ✅ Fase 1 completa | ✅ Confirmado — mas achamos e corrigimos um bug (`login()` descartava o `Response` injetado, cookie nunca saía) |
| Dashboard | ✅ Fase 2 completa | ❌ Estava **quebrado em produção** — `/dashboard/stats` nunca existia no backend (404). **Corrigido** nesta sessão. |
| Produtos | ✅ Fase 3 completa, 13 testes | ❌ Estava **quebrado em produção** — `price_min`/`price_max`/`commission` são `TEXT` no banco, frontend chamava `.toFixed()` numa string, crash total da página. **Corrigido**. |
| Listas de produtos | ✅ Fase 4 completa | ⚠️ Funcionando, mas junto com Produtos/Posts/Credenciais/Usuários sofria do bug do redirect 307 (ver abaixo) — **corrigido**. |
| Posts (thread, IA, agendamento) | ✅ Fase 5 completa | Não testado end-to-end nesta sessão (sem posts cadastrados pra verificar na prática). Mesmo bug de redirect 307 afetava `GET/POST /posts` — corrigido. |
| Credenciais | ✅ Fase 6 completa (Threads OAuth incluso) | Mesmo bug de redirect 307 no `GET /credentials` — corrigido. Não testei o fluxo OAuth do Threads em produção. |
| Usuários | ✅ Fase 7 completa | Mesmo bug de redirect 307 — corrigido. |
| Scheduler | ✅ Fase 8 completa (in-process, bridge HTTP) | Não testado nesta sessão. |
| Notificações (sino do TopBar) | Não estava no roadmap/checklist como item — mas existia visualmente | ❌ Era **decorativo**, sem `onClick`, sem endpoint. **Implementado agora do zero** (reaproveita tabelas `activities`/`activity_types` que já existiam no banco pro painel Flask legado). |

## Bugs corrigidos nesta sessão (2026-09-27) — 4 PRs mescladas em `master`

1. **Cookie de login nunca era enviado** — `login()` criava um `Response()` próprio em vez de usar o injetado pelo FastAPI; retornar um `dict` descartava esse `Response` e o `Set-Cookie` nunca saía. Login "funcionava" (200) mas toda rota autenticada seguinte dava 401.
2. **`/dashboard/stats` nunca existia** — endpoint novo, contando produtos/listas/posts/agendamentos por usuário.
3. **Redirect 307 vazando `127.0.0.1` pro navegador** — o bug mais grave: `products`, `lists`, `posts`, `users`, `credentials` tinham a rota de listagem em `@router.get("/")` sob um prefixo, path canônico com barra (`/products/`), frontend chamava sem barra (`/products`). Em produção, o proxy interno Flask→FastAPI (`127.0.0.1:8001`) deixava esse endereço interno vazar no header `Location` do redirect — o navegador tentava seguir pra um host inacessível e falhava com "Failed to fetch". Isso quebrava **produtos, listas, posts, credenciais e usuários simultaneamente**. Fix: rotas declaradas sem a barra, eliminando o redirect.
4. **`price_min`/`price_max`/`commission` são `TEXT` no banco** — schema legado do scraper armazena esses campos como texto; o Postgrest devolve string, o frontend espera número e chama `.toFixed()`, crash. Fix: normalização pra `float` na API.
5. **Feature nova: sino de notificações** — `GET /notifications` reaproveitando `activities`/`activity_types`, dropdown no frontend com badge de não-lido real (baseado em `localStorage`, já que a tabela não tem coluna de "lido").

Todos com testes automatizados (pytest) e validados manualmente (curl em produção + Playwright local pro frontend).

## Pendências reais — o que falta entregar no mínimo

Cruzando `docs/CHECKLIST_MIGRACAO.md` + `docs/ROADMAP_MIGRACAO.md` com o estado real:

### Bloqueiam aposentar o Flask (`web/`)
- [ ] **Decidir topologia de deploy da API nova em produção.** Hoje o Flask e o FastAPI já rodam no mesmo container (Dockerfile + gunicorn hooks, conforme `api/README.md`) — isso parece **já resolvido na prática** (o proxy `/api/*` está funcionando, é onde achamos o bug do redirect). Vale confirmar se o checklist só está desatualizado nesse ponto.
- [ ] **Fluxo OAuth do Threads** — `api/threads_oauth.py` existe e está implementado (Fase 8.1), mas o checklist ainda marca como pendente migrar a rota legada `/credentials/threads/save?code=` do Flask. Não testei isso em produção nesta sessão.
- [ ] `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` configurados em produção — não verifiquei se essas env vars estão setadas no Render (só confirmei que o serviço sobe e responde).

### Publicação real nas redes sociais — documentação desatualizada, achado nesta sessão
- ⚠️ **`docs/ROADMAP_MIGRACAO.md` e a docstring de `api/routers/posts.py` dizem que só Threads publica de verdade** ("as outras 4 redes têm credencial e roteamento, mas nenhum wrapper de publicação ligado ao scheduler ainda"). **Isso está desatualizado**: verifiquei `scheduler/bot_post_x.py` (115 linhas), `bot_post_facebook.py` (60), `bot_post_instagram.py` (66) e `bot_post_tiktok.py` (91) — todos implementados de verdade (ex: `bot_post_x.py` tem refresh de token, chamada real à API do X, log de atividade) e importados explicitamente em `scheduler/__init__.py` (comentário `# dynamic called functions | DO NOT REMOVE`). **Não testei se publicam de verdade em produção**, mas o código existe e está conectado — não é mais "falta implementar", é "falta validar". Alguém corrigiu isso sem atualizar o roadmap.
- [ ] Kwai fica de fora até existir API pública confirmada (decisão já documentada, não é pendência).
- [ ] **Ação recomendada**: atualizar `docs/ROADMAP_MIGRACAO.md` (Fase 5) e a docstring de `api/routers/posts.py` pra refletir que os wrappers existem, e testar cada rede em produção pra confirmar que publicam de verdade (só isso ainda não foi validado).

### Coisas que podem estar desatualizadas no CHECKLIST
- [ ] O checklist lista como "bug conhecido, não corrigido" que `supabase` em `api/database.py` seria uma função em vez de instância — **isso já está corrigido** no código atual (`_SupabaseProxy` como objeto lazy). Ou o checklist está desatualizado, ou foi corrigido por outra sessão sem atualizar o doc.

### Notificações (feature nova desta sessão)
- [ ] A tabela `activities` está **vazia em produção** — o bot/scheduler nunca gravou nada nela ainda (verificado via Supabase MCP). O dropdown vai aparecer vazio até o scheduler/bot de fato chamar `insert_activities` (já existe em `database/activities.py`, usado pelo Flask legado) — vale confirmar se esse código de fato é chamado nos fluxos de publicação/agendamento atuais, ou se ficou órfão.

### Coisas fora do meu alcance nesta sessão (peço confirmação)
- [ ] Validar em produção, na prática (não só via curl), o fluxo completo: login → produtos → criar lista → criar post → agendar → publicar → aparecer em atividades/notificações.
- [ ] Conteúdo real do vault local (ADRs, relatório de segurança, notas de deploy) — preciso que você compartilhe pra eu reconciliar/atualizar de verdade.

## Próximos passos sugeridos

1. Você compartilha os arquivos do vault local (ou roda uma sessão local do Claude Code com acesso a ambos) pra eu fundir o conteúdo real aqui.
2. Decidir se vale testar manualmente o fluxo de posts/agendamento/publicação em produção agora que os bugs de conectividade foram corrigidos.
3. Avaliar se os wrappers de publicação das redes que faltam (X, Facebook, Instagram, TikTok) entram no escopo "mínimo" ou ficam pra depois.
4. Revisar e atualizar `docs/CHECKLIST_MIGRACAO.md` riscando os itens que já foram resolvidos (o bug do `supabase()`, por exemplo).
