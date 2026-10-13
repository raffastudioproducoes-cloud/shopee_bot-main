# MEMORY — Shopee Auto Vendas

> Estado atual do projeto AGORA. Fonte primária: vault Obsidian
> `Projetos/ShopeeAutoVendas/00-INDICE-Estado-Atual.md` (cruzado com código + consulta SQL
> read-only ao Supabase pelas sessões anteriores) + verificação direta do código nesta
> sessão (2026-09-29). Este arquivo é um resumo local; o vault continua sendo a fonte viva
> mais detalhada — não duplicar histórico de sessão aqui, só o estado atual.

## Repositório

- `C:\Users\rafae\Documents\Projetos\ShopeeAutoVendas\shopee_bot-main`, branch `main` (trabalho em `feature/*`; v2.0.0, ver `CHANGELOG.md`).
- Hospedagem: Render (Free), `https://shopee-bot-fj0w.onrender.com`. Banco: Supabase
  (projeto `autovendas`).
- Flask (legado, produção) e FastAPI (novo) coexistem no **mesmo container Docker** —
  implementado no código (Fase 8.1), validação em produção real ainda pendente.

## Atualização 2026-10-10 — Regra de isolamento

- A interface e API primárias são React/FastAPI. O OAuth usa configurações globais do app de
  cada rede, mas cada autorização, token, luz de status e publicação pertence ao par
  `user_id` + `profile_id` que iniciou o fluxo.
- Callback OAuth com `state` de outro perfil é rejeitado. Publicadores e atualização Shopee
  recusam jobs sem perfil, em vez de procurar uma credencial por usuário e arriscar misturar
  contas entre perfis.
- O painel Flask legado de credenciais permanece desligado por padrão
  (`LEGACY_PANEL_ENABLED=false`). Não reativar sem tornar todas as suas leituras/escritas
  explicitamente multi-perfil.
- Evidência local desta alteração: 20 testes do scheduler e 100 testes API focados em OAuth,
  credenciais e posts. Ainda é necessário validar o fluxo completo no staging antes de merge.

## Redes sociais conectadas — estado real (não o desejado)

| Rede | Estado real |
| --- | --- |
| **Threads** | Único caso com `access_token` de usuário de fato salvo no Supabase. Publicação real em produção não confirmada nesta verificação. |
| **X (Twitter)** | App único configurado (env vars), botão "Conectar X" existe no frontend, mas `user_access_token` está nulo — nenhum usuário concluiu o OAuth. |
| **Instagram** | Mesma situação do X — app configurado, `user_access_token` nulo. |
| **Facebook** | Migrado de token de Página colado manualmente para OAuth de app único (reaproveita o app do Instagram). Credencial nunca validada com sucesso confirmado ("Testar conexão"). |
| **TikTok** | App único configurado, domínio/prefixo e redirect staging validados. Rafa confirmou conexão/autorização no staging em 2026-10-09; publicação real/Direct Post ainda precisa de teste separado (`apis/tiktok.py`, `.env-example`). |
| **Kwai** | Sem API pública de postagem confirmada (só API de anunciantes/ads). Frontend mostra "em breve" para usuário comum. |

Só existe **1 usuário em produção** (`rafastudio`, ADMIN) — confirmado via SQL read-only.

## Decisões importantes recentes (mais recente primeiro)

1. **Migração app-por-usuário → app-único de OAuth** (X, TikTok, Instagram, depois
   Facebook) — o dono do SaaS registra um único app por rede; o usuário final só clica
   "Conectar" e autoriza, nunca cola client_id/secret. Detalhe completo:
   `27-Migracao-App-Unico-OAuth.md` (vault). Facebook exigiu reforma maior: o mecanismo
   anterior (App Access Token + `/me/accounts`) só via Páginas do próprio app, não de
   usuários do SaaS — precisou de OAuth de usuário de verdade.
2. **Histórico de requisições (`request_logs`)** — a pedido do dono do projeto ("não quero
   mais passar print de cada erro"), toda requisição à API nova é registrada (método, path,
   status, duração, usuário, redirect de callback OAuth). Desligado por padrão, ligado em
   produção via `REQUEST_LOGGING_ENABLED=true`. Detalhe: `28-Historico-de-Requisicoes.md`
   (vault).
3. **Coexistência no mesmo container** em vez de dois Web Services Render separados —
   decisão por custo/complexidade (plano Free do Render).
4. **Scheduler in-process** mantido (ADR 19, vault) — sem worker separado; gatilho de
   revisão ainda não disparou.
5. **Fluxo padrão de credenciais** — TikTok é OAuth disponível para usuário comum, como
   Threads, X, Facebook e Instagram. Shopee e chave de IA são as únicas entradas manuais do
   cliente padrão; overrides sociais/Kwai são ferramentas ADMIN-only protegidas também no backend.
6. **Telemetria de publicação sem segredos** — cada disparo manual e cada resultado do
   scheduler registra rede, post, job e etapa em `request_logs`/`activities`; o erro do
   provedor é preservado para diagnóstico, mas tokens, senhas, chaves, hashes, cabeçalhos
   Basic/Bearer e parâmetros OAuth são mascarados antes da persistência.

## Atualização 2026-10-10 — contrato de OAuth e mídia

- Antes de abrir qualquer provedor OAuth, a tela de Credenciais mostra um aviso de consentimento
  com rede, dados solicitados, autorização de publicação e como desconectar.
- Cada token, status e publicação continua isolado por `user_id` + `profile_id`; a configuração
  do aplicativo OAuth é global apenas no servidor.
- Threads, Facebook e Instagram têm caminho de imagem no código. X ainda exige implementação
  de upload de mídia e crédito/API habilitada; TikTok Photo Direct Post exige URL pública no
  domínio/prefixo verificado e Creator Info no fluxo de usuário. Vídeos seguem pendência
  explícita e não podem ser tratados como validados por testes de imagem.

## Atualização 2026-10-11 — composição de mídia multi-rede

- A criação multi-rede passa a tratar texto e mídia como uma composição por rede, não como a
  mesma lista de arquivos enviada indistintamente a todas elas.
- A decisão de produto é publicar nas redes compatíveis mesmo que outra tenha restrição. Quando
  a mídia não for aceita, essa rede recebe somente texto válido quando sua API permitir post
  textual; caso contrário, ou se não houver variante válida, apenas ela fica fora do envio.
- As abas de texto existentes seguem por limite. Abas adicionais de mídia só aparecem quando
  redes selecionadas precisarem de formatos diferentes, como foto única, carrossel ou vídeo.
- O backend precisa repetir a validação e manter cada ativo no mesmo `user_id` + `profile_id`.
  A especificação aprovada está em
  `docs/superpowers/specs/2026-10-11-composicao-midia-por-rede-design.md`; a implementação
  está registrada na atualização de 2026-10-12 abaixo.

## Atualização 2026-10-12 — publicação de mídia e agendamento (branch `staging`, só local)

Estado: implementado e coberto por testes locais; **não validado em staging** e `VERSION`
continua `2.1.0`. Nada foi enviado ao remoto nem aplicado no Supabase.

- **Capacidades reais por rede** (`api/network_limits.py`, espelhado em
  `frontend/src/lib/networkLimits.ts`): `platform_modes` é o que a rede aceita;
  `delivered_modes` é o que o publicador realmente entrega, e o planejador só devolve modo
  entregue. Threads: nenhum, foto única, carrossel, vídeo e só texto. X: nenhum, foto única e só
  texto (sem carrossel nem vídeo). Facebook: nenhum, foto única, carrossel (álbum), vídeo e só
  texto. Instagram: foto única, carrossel e vídeo (Reels), sem texto puro. TikTok: somente
  vídeo; foto bloqueada.
- **Rascunhos de mídia** (migração `046_add_durable_media_drafts.sql`): upload antes de criar
  post, em `temporary_media_uploads` + bucket privado `post-media` (50 MB, jpeg/png/gif/webp/mp4,
  RLS ligado, sem acesso do navegador). Escopo `user_id` + `profile_id`; expira em 24 h
  (`MEDIA_DRAFT_TTL`); estados `uploading/ready/consumed/delete_failed`. Cancelar rascunho nunca
  apaga ativo já vinculado a `posts_medias`.
- **`POST /posts/preview` e `POST /posts/batch`**: o preview recalcula o plano por rede sem
  gravar nada; o batch gera o `group_id` no servidor, cria só as redes entregáveis (criação
  parcial) e devolve `created` e `blocked` sem detalhe bruto de provedor. Falha ao agendar uma
  rede desfaz só aquela rede.
- **Recorrência até 7 dias** (migração `047_add_scheduler_days_of_week.sql`): coluna
  `schedulers.days_of_week` (1 a 7 valores de 0 a 6, validada no banco e na API). Jobs legados com
  só `day_of_week` seguem válidos; a migração copia o dia único dos cron existentes.
- **Publicadores**: Threads, Facebook (foto, álbum, vídeo), Instagram (foto, carrossel, Reels) e
  X (foto única com `media.write`) entregues no código. Facebook, Instagram e Threads recebem URL
  assinada (1 h, `scheduler/media_delivery.py`) do bucket privado; mídia legada segue pelo
  Cloudinary. **TikTok foto segue bloqueado** até haver Creator Info no fluxo do usuário e URL em
  domínio/prefixo verificado; TikTok vídeo não mudou.
- **Evidência local (2026-10-12)**: `tests/api` 536 passed, `tests/scheduler` 75 passed,
  `tests/database` 3 passed, testes node do frontend 10 passed, `npm run build` ok,
  `git diff --check` limpo, sem segredos nos commits novos. Sem teste real em nenhuma rede.

Pendências conhecidas desta entrega:

- X exige o escopo `media.write` habilitado no portal de desenvolvedor; conexões antigas sem
  ele recebem 401/403 e precisam reconectar. O escopo concedido não é persistido, então o
  sistema não sabe antecipadamente quais conexões estão sem ele.
- A API do Facebook segue fixa em `v18.0` (`apis/facebook.py`); revisar versão suportada.
- A ordem das mídias no post é incidental: `display_order` segue a ordem dos rascunhos no
  pedido, sem garantia de contrato por rede.
- O scheduler precisa de `SUPABASE_URL`/`SUPABASE_KEY` (chave de servidor) para assinar URL;
  sem elas a publicação de mídia durável falha. Conferir no ambiente de staging.

## O que falta (real, não aspiracional)

- Cadastrar a callback URL de cada rede no painel de desenvolvedor correspondente (X
  Developer Portal, Meta for Developers, TikTok for Developers) — a env var já está no
  Render.
- Clicar "Conectar" e autorizar de fato em X, Instagram e TikTok — ação humana, não código
  faltando.
- Validar em produção real no Render que o subprocesso uvicorn sobe corretamente e que
  `FLASK_INTERNAL_URL`/`INTERNAL_API_SECRET` estão configurados.
- Testar publicação real de Threads e Facebook em produção (credenciais existem, nenhum
  sucesso confirmado até a última verificação do vault).
- Recolar o Client Secret do TikTok na tela de credenciais (não dá para inspecionar um
  segredo cifrado às cegas para confirmar se ainda carrega espaço em branco).
- Kwai permanece fora até existir API pública de postagem confirmada — decisão antiga, não
  pendência nova.

## Nota de precisão sobre o contexto desta tarefa

O contexto fornecido junto com a instrução desta rodada de documentação afirmava que
"Threads, X, Facebook, Instagram — funcionando end-to-end (OAuth completo, testado e
confirmado)". A evidência real (código + consulta SQL ao Supabase, registrada no vault em
2026-09-28) **não confirma essa afirmação**: só o Threads tem token de usuário de fato salvo.
As outras três têm o mecanismo de OAuth implementado e a UI pronta, mas nenhum usuário
completou a conexão. Esta tabela e o restante do documento refletem o estado real, não o
contexto inicial.

## Atualização 2026-10-05 (nota datada; o conteúdo acima é de 2026-09-29)

- **Branch de trabalho**: `chore/phase-12-integration` (worktree `wt-int`). Segundo
  `git log main..HEAD`, estes commits ainda não estão em `main`; `VERSION` segue 2.0.0 e as
  mudanças estão em `CHANGELOG.md` como "Não lançado".
- **Feito no código desta branch**: multi-perfil completo (`profile_id` em 16 tabelas, migrações
  até 041, backup/restore e bots por perfil), UI de perfis (editar/excluir/ativar/TopBar),
  segurança do servidor (claim `pwv`, validação do `profile_id`, trigger 037, rate limits),
  Dockerfile não-root + `HEALTHCHECK`, gunicorn com timeout e supervisão, CI/CD endurecidos.
- **Estado das redes**: TikTok passou a ter conexão/autorização confirmada no staging em
  2026-10-09. X/Instagram ainda dependem de alguém clicar "Conectar" depois do painel de
  desenvolvedor aceitar a callback URL. Threads continua conectado para `rafastudio`/AMD.
- **Pendências manuais de Rafa (não são código) — atualizado 2026-10-05**:
  - [CONCLUÍDO] Env vars do serviço `shopee-bot-staging` no Render (copiar as de produção) — confirmado pelo Rafa, 2026-10-05.
  - [CONCLUÍDO] Trocar o branch de produção do serviço no Render de `master` para `main` — confirmado pelo Rafa, 2026-10-05.
  - [CONCLUÍDO] Secret `RENDER_STAGING_DEPLOY_HOOK_URL` no GitHub — confirmado pelo Rafa, 2026-10-05.
  - [CONCLUÍDO] Cadastrar as callback URLs de cada rede (X, Meta, TikTok) nos painéis de desenvolvedor — confirmado pelo Rafa, 2026-10-05.
  - [CONCLUÍDO] Conectar X, Instagram e TikTok (ação humana: clicar "Conectar" e autorizar) e recolar o Client Secret do TikTok — confirmado pelo Rafa, 2026-10-05.
  - [POSSÍVEL, NÃO ATIVADA] Branch protection: exige GitHub Pro ou repositório público (GitHub Free não oferece em repo privado) — GitHub Pro ativo (confirmado pelo Rafa, 2026-10-05), mas branch protection ainda não configurada.
  - [CONCLUÍDO, 2026-10-06] Aplicar as migrações 037, 038, 039, 040, 041 e 042 no Supabase — verificado via MCP: 6 migrações registradas em `public.migrations` (linhas); nenhum `profile_id` NULL em `posts`/`shopee_credentials` após backfill. Ver `docs/RULES.md` item 11 para procedimento e risco conhecido sobre restore com código antigo.
  - Merge dos PRs da branch `chore/phase-12-integration` em `main`.

## Atualização 2026-10-09 — evidência atual de OAuth Threads/TikTok

Registro feito antes de qualquer correção de código, a partir das telas enviadas pelo Rafa e
da leitura do fluxo em `api/routers/credentials.py`, `api/threads_oauth.py` e
`api/tiktok_oauth.py`. Nenhum token, segredo ou valor sensível foi lido ou salvo.

- **Threads:** a conta `rafastudio`/AMD conecta e aparece como `Funcionando` em staging.
  A conta de usuário comum falha no provedor com
  `Invalid Request: The user has not accepted the invite to test the app.`
  (`error_code=1349245`). Isso aponta para bloqueio externo do app Threads/Meta em modo de
  teste: o usuário precisa ser adicionado como tester/role e aceitar o convite, ou o app
  precisa estar aprovado/liberado para público. Não é evidência de token ou callback quebrado
  no backend.
- **TikTok:** o botão `Conectar TikTok` chega ao provedor, mas o TikTok rejeita antes do
  callback com erro de `redirect_uri`. O backend aceita `/api/credentials/tiktok/callback`
  e `/api/credentials/tiktok/callback/`; o painel TikTok precisa ter exatamente a URL que
  está em `TIKTOK_CALLBACK_URL` para cada ambiente, e para TikTok também convém manter a
  variante com barra final por causa da verificação de prefixo. Só depois disso o usuário
  deve clicar em `Conectar TikTok`/`Reconectar TikTok` para gerar novo token via OAuth.
- **Renovação de token TikTok:** não se troca token manualmente pelo portal. O token novo é
  obtido pelo OAuth; o scheduler só consegue renovar quando já existe `refresh_token` salvo
  por uma conexão anterior bem-sucedida.

### Atualização dentro de 2026-10-09 — causa real do staging TikTok

- A tela do TikTok for Developers mostrou que o **Login Kit > Production > Live** tinha
  somente a Redirect URI de produção cadastrada:
  `https://shopee-bot-fj0w.onrender.com/api/credentials/tiktok/callback`.
- O staging usa outra Redirect URI:
  `https://shopee-bot-staging.onrender.com/api/credentials/tiktok/callback`.
  Enquanto essa URL não estiver cadastrada na revisão Live do Login Kit, o TikTok rejeita
  `Conectar TikTok` no staging com erro de `redirect_uri`.
- O botão `URL properties`/`URL prefix` pediu um arquivo novo:
  `tiktoksuFLmrUFUxZQioEp5TCgDiOi0VAiY2e1.txt`, servido em staging por
  `/api/credentials/tiktok/callback/tiktoksuFLmrUFUxZQioEp5TCgDiOi0VAiY2e1.txt`
  no commit `12d1720`. A URL pública respondeu `200` com o conteúdo esperado antes de orientar
  o Rafa a clicar em `Verify`.
- Próxima ação operacional: criar revisão no TikTok for Developers, adicionar a Redirect URI
  de staging na aba Web do Login Kit sem remover a de produção, salvar/publicar a revisão e só
  então testar `Conectar TikTok` no staging.
- **Resolvido no staging:** Rafa confirmou em 2026-10-09 que a conexão/autorização do TikTok
  funcionou, o app voltou do provedor e a conta ficou conectada.

## Atualização 2026-10-11 — contrato de conta, perfil e acesso

- O limite é de três perfis por conta, incluindo o principal.
- Shopee, IA e produtos salvos pertencem a `user_id`; ao criar ou alternar perfil eles continuam
  disponíveis sem duplicar segredo ou catálogo.
- Redes OAuth, checks/status, listas, posts, mídias, jobs, resultados e preferências pertencem
  ao par `user_id` + `profile_id`. Nunca usar credencial social de outro perfil.
- USER vê apenas fluxo OAuth para redes sociais e formulários próprios de Shopee/IA. ADMIN tem,
  em módulos carregados somente depois da confirmação de papel pelo servidor, gestão de contas,
  logs e overrides manuais para homologação.
- A migração 045 está pronta no `staging`, com preflight de divergência. Ainda precisa ser
  aplicada/confirmada no banco de staging após o deploy. A versão do produto foi elevada para
  `2.1.0` somente no fechamento das tarefas da migração.
- Evidência local da migração: 511 testes de API passaram; build do frontend passou e gerou
  chunks separados para UsersPage, LogsPage e AdminOverrides. O scheduler requer PostgreSQL de
  teste configurado e não foi apontado a nenhum banco remoto nesta validação.

## Referências

- Vault Obsidian: `00-INDICE-Estado-Atual.md` (fonte viva mais detalhada, rede a rede,
  cruzada com Supabase), `27-Migracao-App-Unico-OAuth.md`, `28-Historico-de-Requisicoes.md`,
  `26-Deploy-Render.md`
- `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`
