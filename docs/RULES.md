> **08/11/2026 — RELEASE AUTO ORBITAL 3.7.0 EM PRODUÇÃO (ESTADO CANÔNICO):** Rafa autorizou a promoção da galeria de Produtos para campanhas, posters MP4 e progresso animado. PR #374/CI #1185 SUCCESS → staging `f34dd11`, Render `dep-dboh06o473hc73akd7bg` LIVE; PR #375/CI #1187 + SemVer #14 SUCCESS → main `a16f569ca8ebbbbb834bc7b909abe85407dafc3c`, Render produção `dep-dboh27e8bjmc73b7ukfg` **LIVE**. Saúde/prontidão/login 200, HTML 3.7.0, poster privado sem sessão 401, sem novos requests 5xx observados (`SIGTERM` de worker antigo esperado). `VERSION=3.7.0`, zero diferenças de arquivos main/staging no merge. Sem migração/cron/gateway/segredo/postagem real; QA autenticada em produção não realizada pelo agente. [Release e limites](RELEASE-3.7.0-20261108.md). Registros anteriores '3.7.0 em preparação' ou 'main 3.6.2' são históricos.

> **08/11/2026 — PROMOÇÃO MINOR AUTO ORBITAL 3.7.0 AUTORIZADA:** Rafa aprovou expressamente o merge da funcionalidade de mídia/miniaturas da staging para a main. Bump SemVer `3.6.2 → 3.7.0` em `VERSION` e seção datada de `CHANGELOG` preparados na branch de release; PR para staging, CI, Render staging LIVE, gate SemVer do PR main e Render produção LIVE são pré-condições. A implantação em main **ainda não está comprovada neste registro preparatório**. Sem migração/cron/segredo/alteração de publicação. [Roteiro de release](RELEASE-3.7.0-20261108.md).

> **08/11/2026 — NOVO CONTRATO DE MÍDIA, EM PREPARAÇÃO:** a campanha não faz novo upload: UUIDs da galeria devem ser revalidados no servidor por conta, produto e `ready`, copiados para Storage privado do perfil antes da ativação, preservando anexos legados e idempotência. Foto Shopee/mídia adicional podem ser desligadas, mas redes que exigem mídia continuam bloqueando combinações inválidas. Poster real de vídeo privado com cache; não simular percentual de FFmpeg. Release somente após CI, staging e aprovação. **MINOR candidata 3.7.0**, `VERSION=3.6.2` mantida. [Contrato](CAMPANHA-MIDIAS-PRODUTO-20261108.md).

> **08/11/2026 — ESTADO CANÔNICO: AUTO ORBITAL 3.6.2 EM PRODUÇÃO.** Rafa homologou a correção do HTTP 502/cronômetro em staging e autorizou PATCH e main. PR #368/CI #1172 SUCCESS → staging `13d74a0f`, Render `dep-dbofjam8bjmc73b6gkrg` LIVE; PR #369/CI #1174 + gate SemVer #12 SUCCESS → main `bf558c644d6f42b28baccf766eff0825e17a1d17`, Render produção `dep-dbofl50ae00c739m8bq0` LIVE. Health/readiness/login 200 e HTML público 3.6.2, sem novo request 5xx observado; `SIGTERM` do worker antigo esperado. `VERSION=3.6.2`, staging/main com arquivos idênticos; sem migração, cron, gateway ou postagem real. QA autenticada pelo agente em produção não feita. [Release e limites](RELEASE-3.6.2-20261108.md). Notas anteriores sobre 3.6.1 vigente/staging-only são históricas.

> **08/11/2026 — REGRA DE RELEASE 3.6.2:** aprovação expressa de Rafa para levar correção do upload 502/cronômetro de staging à main após bump PATCH 3.6.1→3.6.2, CI/SemVer verdes e Render produção LIVE. [Portões e limitações](RELEASE-3.6.2-20261108.md). Sem alterar controle de mídia, Supabase, cron, redes ou custos.

> **08/11/2026 — REGRA DE PROXY DE MÍDIA (PATCH candidata 3.6.2, apenas staging):** POST de mídia de Produtos pode exceder 30 s de processamento seguro; expandir somente essa rota para conexão/leitura `(5,180)` s; outras APIs preservam 30 s. Timeout HTTP 504 e indisponibilidade 502; não duplicar upload com resultado incerto. Círculo mostra bytes reais e cronômetro mostra tempo real decorrido, sem percentuais simulados da conversão. [Contrato](UPLOAD-502-TEMPO-PROCESSAMENTO-20261108.md). `main`/`VERSION=3.6.1` protegidos até autorização.

> **08/11/2026 — EVIDÊNCIA NOVA:** PR app #366/CI #1168 **SUCCESS** → staging `33d73d97572ce0ee736d535f1cbfe35a11bb3314`, Render `dep-dboep9qvcj2c739apqug` **LIVE**, health/readiness/login HTTP 200. Testes locais 1.308 API, 34 web, 33 frontend correlatos, 5 SemVer e build PASS. **Ainda falta QA autenticada de Rafa; sem merge main nem bump de VERSION=3.6.1.** [Registro técnico](UPLOAD-502-TEMPO-PROCESSAMENTO-20261108.md).

> **08/11/2026 — RELEASE 3.6.1 EM PRODUÇÃO (REGRA VIGENTE):** correção MP4 `uuid` com pré-validação limitada, FFmpeg obrigatório e validação final estrita; não afrouxar sanitização de arquivo armazenado. Progresso circular mede bytes reais e distingue processamento servidor. SemVer PATCH 3.6.0→3.6.1 aprovada por Rafa, PR #363 CI/SemVer SUCCESS, Render produção LIVE, saúde OK. [Decisões, QA e SHAs](RELEASE-3.6.1-20261108.md). Não ativar cron, gateway, RLS ou nova publicação por inferência.

> **08/11/2026 — NOVA REGRA DE MÍDIA (EM HOMOLOGAÇÃO STAGING):** rejeições de MP4 `uuid` devem ser corrigidas preservando a segurança: a caixa opaca pode ser admitida com tamanho/quantidade limitados **somente** no preflight que garante transcodificação obrigatória; bytes persistidos passam pelo validador original estrito e não contêm a caixa original. Percentuais de upload são eventos medidos (`XMLHttpRequest.upload.onprogress`), nunca simulação de conversão/Storage. Nenhuma mídia real é postada para testar. [Contrato](UPLOAD-MP4-PROGRESSO-20261108.md); `VERSION=3.6.0`, candidata PATCH 3.6.1 staging, main protegida até aprovação. O estado atual de produção continua aquele registrado para 3.6.0 abaixo.

> **08/11/2026 — ESTADO OPERACIONAL CANÔNICO: AUTO ORBITAL 3.6.0 EM PRODUÇÃO.** [PR #357](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/357) promoveu staging→main depois de CI #1150 e gate SemVer #8 SUCCESS; `main` SHA `699e81bd18e2b12fc3824f914045627a45844cc2`, Render `dep-dbod0q7b9u1s73dhci7g` LIVE, `/health` e `/api/health/ready` OK, CI push #1151 SUCCESS. MINOR 3.5.0→3.6.0: download seguro de imagem Shopee e herança da descrição-base em novos posts/campanhas com variantes IA isoladas. **Sem alteração em cron, Supabase ou gateway.** [Evidência e limites](RELEASE-3.6.0-20261108.md). Notas sobre 3.5.0 como versão atual são históricas; QA autenticada/CDN/IA real segue pendente.

> **07/11/2026 — RELEASE E VARREDURA:** a release 3.5.0 foi promovida por PR #350 staging → #351 main, CI #1136/#1138 e SemVer #6 verdes, Render produção LIVE e readiness 200. Notas anteriores que indicam 3.4.0/staging-only são históricas. Cada solicitação futura de **varredura** exige seguir [SEGURANCA-VARREDURA-CHECKLIST.md](SEGURANCA-VARREDURA-CHECKLIST.md), atribuir riscos somente com evidência e atualizar [relatório de 07/11](SEGURANCA-AUDITORIA-20261107.md) no novo SHA; mudanças de segurança seguem testes/PRs, sem alterar banco compartilhado, cron, custos ou produção durante diagnóstico.

> **04/11/2026 — DECISÃO VINCULANTE DO PROPRIETÁRIO:** antes de recomendar qualquer serviço/migração ou emitir alerta operacional, ler estado canônico, código implantado, cron/funções/logs do Supabase e Render. Verificado diretamente: cron `auto-orbital-wake-v1` a cada 2 min chama `app_internal.wake_dispatch_if_needed`, com `pg_net` e Vault; os agendamentos já possuem mecanismo de wake no plano atual. Rafa não autoriza migração nem alteração desse fluxo. Nunca confundir cron SQL com confirmação externa de publicação. Ver AGENTS.md e ARCHITECTURE.md.

> **14/11/2026 — ESTADO DAS REDES (Rafa):** Facebook, Instagram, Threads e TikTok funcionam em produção; X reativado por decisão do Rafa (cliente único em teste; falha por crédito da API é aceita e deve aparecer como erro claro, sem retry). Instagram exige conta profissional vinculada a uma Página do Facebook. Bloqueio de rede por regra de produto continua possível via `DISABLED_NETWORKS` (hoje vazio).

> **04/11/2026 — CONTRATO DE DISPONIBILIDADE (Rafa):** `main` atende clientes e não pode ser intencionalmente pausado; `staging` recebe desenvolvimento/testes; Supabase, API, backend e serviços compartilhados permanecem operando continuamente. Toda migration é aditiva/compatível com main, CI e smoke obrigatórios antes do merge, deploy sem interrupção, readiness/logs após. VERSION+CHANGELOG são lidos antes de qualquer trabalho para decidir MAJOR/MINOR/PATCH/sem bump. Intervenção que exija parada: somente com decisão de Rafa, aviso a todos os usuários pelo menos 24h antes com duração e aviso posterior de retorno. Render Free (ambos sites) pode hibernar, mas a execução de publicações conta com `pg_cron`/`pg_net` no Supabase que desperta o Render sob demanda quando há trabalho; **não usar essa hibernação como motivo automático para propor upgrade/migração**. Conferir cron real, logs, estado dos jobs e código antes de afirmar falha. Migração proibida sem nova autorização expressa. Detalhes em AGENTS.md e TASK.

> **02/11/2026 — Correção de isolamento entre os schedulers de staging e main (implantação em etapas):** o mesmo Supabase permanece, mas agendas novas terão `schedulers.environment` conforme o branch Render; jobs anteriores ficam na produção. APScheduler passa a usar `apscheduler_jobs` em main e `apscheduler_jobs_staging` em staging; recuperação/claims da fila verificam o ambiente e dono. Ativação de staging só depois de a main receber estes filtros. Detalhes, verificação e rollout em [SCHEDULER-ENVIRONMENTS-20261102.md](SCHEDULER-ENVIRONMENTS-20261102.md). Nenhuma publicação externa é validada por CI.\n\n> **02/11/2026 — Correção dos posts em desenvolvimento (staging, ainda não publicada):** seleção de um produto, retirada de agendamento avulso, seletor desktop em 24h, histórico do estado de cada ocorrência, última postagem confirmada e erro simplificado para usuário. Supabase compartilhado impede apagar esquema/legado; erro HTTP 403 do Threads precisa de código Meta e autorização antes de declarar publicação funcionando. Detalhes e QA: [POSTS-AJUSTES-RECORRENCIA-20261102.md](POSTS-AJUSTES-RECORRENCIA-20261102.md). **Não alterar main/produção.**

> **Regras vigentes de 31/10/2026:** veja o Guia Mestre e o arquivo atual de workflow. CI roda em `main` e `staging`, com testes API, scheduler, SQL e web; esta lista histórica registra o padrão em sua data. **Primeira leitura obrigatória:** [AGENTS.md](../AGENTS.md) e [docs/GUIA-MESTRE-IA.md](GUIA-MESTRE-IA.md).

# RULES — Shopee Auto Vendas

> Regras de desenvolvimento realmente seguidas neste projeto, extraídas do histórico git
> (`git log`), da CI (`.github/workflows/`) e de convenções observadas no código. Cenário A —
> nada aqui é regra genérica de template; cada item tem evidência local citada.

## 1. Commits

Padrão observado em `git log --oneline -100` (contagem real): `feat:`, `fix:`, `fix(web):`,
`feat(migration):`, `fix(api):`, `docs:`, `chore:`, `refactor:`, `ci:`, `debug:`,
`style(login):` — sempre **em português**, minúsculo, descrição curta e objetiva. Escopo
entre parênteses é comum mas opcional (`fix(credentials):`, `feat(tiktok):`,
`feat(oauth):`). Mensagens de corpo longo (quando existem) explicam o *porquê* da mudança,
não só o *o quê* — ver corpo do commit `feat(facebook): OAuth de app unico...`
(`.claude/tmp/commit_msg_facebook_oauth.txt`), que documenta o problema resolvido, a
reutilização de app existente e uma limitação conhecida deixada como MVP.

Fluxo de branches (Git Flow, a partir de 2026-09-30): `main` é produção, `staging` é o
ambiente de homologação e todo trabalho acontece em `feature/*`. Nunca commitar direto em
`main`: trabalho em branch própria + PR, e merge só com testes verdes e revisão. (Antes
disso a prática era push direto em `master` sem PR — confirmado no vault,
`27-Migracao-App-Unico-OAuth.md` — e alguns merges de PR existem no histórico, `#5`, `#4`.)

**Gate automático (release 3.2.0):** além da classificação humana, cada PR de código/configuração/CI direcionada a `main` roda `.github/workflows/release-semver.yml`. Bloqueia merge sem incremento SemVer válido em `VERSION` e seção datada correspondente no `CHANGELOG`; PR somente documental não obriga bump. Não chamar a versão de implantada antes de Render LIVE e logs.

Versionamento SemVer: `VERSION` é a **fonte oficial única** para a versão da aplicação; antes de qualquer alteração, ler `VERSION` e `CHANGELOG.md`. Todo PR deve registrar código, configuração, CI ou documentação em `CHANGELOG.md` sob `[Não lançado]` (sem criar uma versão nova por commit). A versão só é formalizada após homologação em `staging` e promoção aprovada para `main`, mantendo os dois arquivos alinhados nas branches. **MAJOR**: mudança incompatível — incrementa X, zera Y/Z; **MINOR**: funcionalidade compatível — incrementa Y, zera Z; **PATCH**: correção, desempenho ou segurança sem mudar regra de negócio — incrementa Z. Documentação isolada não força bump. O sistema multi-perfil foi tratado como MAJOR (2.0.0); a remoção de agendamento avulso e da seleção múltipla de produtos caracteriza o marco 3.0.0. Após publicar uma versão, criar uma tag Git `vX.Y.Z` na `main` se o fluxo de releases estiver disponível, sem tag duplicada por ambiente.

Proteção de branch: **GitHub Pro está ativo (confirmado pelo Rafa, 2026-10-05).** A proteção
automática de branch agora é possível — branch protection/Rulesets pode ser ativada em
repositório privado com GitHub Pro. Configuração não foi aplicada ainda (possível agora, ainda
não ativada). Ver `docs/TASK.md` item 10.13 para contexto da decisão.

## 2. CI (`.github/workflows/ci.yml`)

- Gatilhos: push e pull_request em `main`. `permissions: contents: read`; `concurrency`
  cancela execuções antigas do mesmo ref. Cache de pip e npm.
- Job `api` (Python 3.13, igual ao `Dockerfile`):
  - `flake8 api/ --select=E9,F63,F7,F82` **bloqueante** (sem `|| true`); estilo
    (`--max-line-length=120`) é informativo (`continue-on-error`).
  - Checagem de sintaxe via `python -m py_compile` nos módulos centrais.
  - Testes: `python -m pytest tests/api --confcutdir=tests/api -q` — **nunca** `pytest` puro
    (quebra `ModuleNotFoundError` em `from api.main import app` sem `-m pytest`).
  - `--confcutdir=tests/api` é obrigatório: o `conftest.py` da raiz faz
    `gevent.monkey.patch_all()` (Flask legado) e trava as threads async do `anyio`/`httpx`.
  - Só cobre `tests/api`; os testes do Flask legado exigem Postgres local em `localhost:5433`
    e **não rodam na CI**.
- Job `frontend` (Node 20): `npm ci` e `npm run build` (`tsc && vite build`) em `frontend/`.
  Não há testes de frontend.
- `.github/dependabot.yml` (semanal, minor/patch agrupados: pip raiz e `/api`, npm, actions)
  e `.github/pull_request_template.md` com checklist de PR.

## 3. Deploy

- `cd.yml` dispara via `workflow_run` quando o workflow `CI` termina com sucesso em `main`
  (evento push). CI vermelho = sem deploy. `concurrency` evita deploys em paralelo.
- `curl -fsS`: resposta HTTP de erro do hook do Render faz o job falhar.
- Se o secret `RENDER_DEPLOY_HOOK_URL` não existir, o job **não falha** — emite `::warning::`
  e sai com `exit 0`. Deploy silenciosamente pulado ainda é possível.

## 4. Padrões de código observados

- **Docstrings extensas e datadas em módulos sensíveis** (OAuth, criptografia, scheduler):
  cada arquivo de app único de OAuth (`api/x_oauth.py`, `api/tiktok_oauth.py`,
  `api/instagram_oauth.py`) documenta no topo do módulo: por que duplica lógica em vez de
  importar entre módulos, o padrão que foi seguido, e um ponteiro para o arquivo do vault
  Obsidian que registra a decisão (`Projetos/ShopeeAutoVendas/27-Migracao-App-Unico-OAuth.md`).
  Seguir esse padrão ao criar um módulo OAuth novo.
- **`.strip()` defensivo em toda leitura de credencial de env var ou form**: aplicado depois
  de um bug real em produção (espaço colado no painel do Render vazando pro Basic Auth
  base64, virando 401 `unauthorized_client` em vez de `invalid_client`). Ver
  `api/x_oauth.py:44-51`, `api/tiktok_oauth.py:26`, e o `PUT /credentials/{network}` genérico
  em `api/routers/credentials.py` (`app_id.strip()` / `secret.strip()`, aplicado a **todas**
  as redes de `SIMPLE_NETWORKS`, não só a que apareceu o bug).
- **Nunca reexibir credencial salva**: toda rota de leitura de credencial devolve status
  (conectado/desconectado), nunca o valor. Confirmado em `api/routers/credentials.py`
  (`_status_only`) e no frontend (`CredentialsPage.tsx` não tem campo de exibição de
  segredo).
- **`check_message` (diagnóstico cru de conexão) só para ADMIN**: usuário comum recebe
  `check_message: null`; luz de status (verde/amarelo/vermelho) é visível para todos.
  Confirmado em `api/routers/credentials.py:183-235` (`list_credentials`).
- **Sem redirect 307 nas rotas da API nova**: todas usam `@router.get("")` /
  `@router.post("")` (sem barra final), evitando redirect que vazaria `127.0.0.1` para o
  navegador em produção. Padrão a seguir em toda rota nova de `api/routers/`.
- **Camada de compatibilidade em vez de import cruzado**: a API nova (`api/`) duplica
  funções puras de OAuth de `apis/` em vez de importar, para não arrastar dependências do
  Flask legado (`shopee_bot.utils`) para `api/requirements.txt`. Mesmo padrão para
  `api/crypto.py` (wrapper Fernet compatível com `utils/crypto.py`).
- **Mudança aditiva, não substitutiva, ao integrar OAuth novo**: `scheduler/bot_post_facebook.py`
  usa o token OAuth quando presente e cai para o fluxo legado (app_id/secret) quando não —
  não quebra contas que ainda não reconectaram.

## 5. Testes

- Cobertura-alvo declarada para a API nova: 80%+ (`api/README.md`, `pytest tests/api
  --cov=api --cov-report=term`).
- Testes do Flask legado e da API nova são **suites isoladas** (`tests/` vs `tests/api/`),
  cada uma com seu próprio `conftest.py`/`confcutdir` — não misturar.
- `flake8` roda sobre `api/`, não sobre `apis/`, `database/`, `web/` (legado) — o lint na CI
  cobre só a camada nova.

## 6. Migrações de banco

- SQL numerado sequencialmente em `database/migrations/` (ex.:
  `023_add_network_to_posts.sql`, `030_add_oauth_fields_to_facebook_credentials.sql`) — sem
  ferramenta de migration automática (Alembic etc.); aplicação manual/documentada.

## 7. Documentação viva

- Este repositório mantém só documentação **técnica de código** (`README.md`,
  `docs/ROADMAP_MIGRACAO.md`, `docs/CHECKLIST_MIGRACAO.md`, e agora os 6 docs canônicos em
  `docs/`). Histórico de decisão, estado de produção e detalhe de sessão vivem no **vault
  Obsidian** (`Projetos/ShopeeAutoVendas/` em `C:\Users\rafae\Documents\Obsidian`), fonte de
  verdade para "o que está feito de fato em produção". O arquivo `vault/00-INDICE-Estado-Atual.md`
  deste repo é só um ponteiro para lá, não uma duplicata.
- Ao encontrar uma afirmação desatualizada em `docs/ROADMAP_MIGRACAO.md`/`CHECKLIST_MIGRACAO.md`,
  o padrão observado é **corrigir com nota datada** em vez de apagar a afirmação antiga
  silenciosamente (ver "Atualizado 2026-09-27 (correção de uma alegação desatualizada desta
  seção)" em `docs/ROADMAP_MIGRACAO.md`).

## 8. Migração de esquema de auth/dado sensível (diretriz, não tarefa isolada)

- Se qualquer mudança futura de esquema de autenticação ou de dado sensível for feita,
  seguir o padrão de fallback para o formato legado durante a transição, sem quebrar conta
  existente (não fazer migração destrutiva de uma vez só). Prática trazida do benchmarking
  contra o projeto MiauDelier Manager (origem: benchmarking MiauDelier Manager, 2026-09-29).
  Ver `docs/TASK.md` Fase 10 para o backlog de segurança/features relacionado.

## 9. Migração aplicada fora do fluxo do app (Supabase MCP direto)

- O app tem seu próprio controle de migração: tabela `public.migrations` (colunas
  `id`, `name`, `aplied_at` — nome com esse typo mesmo, não corrigir sem migrar
  os dados), lida em todo boot via `post_fork` (`web/__init__.py`) →
  `database/__init__.py:init_db()` → `database/migrations/__init__.py:run_migrations()`,
  que roda sequencialmente todo `.sql` em `database/migrations/` que ainda não
  está na tabela.
- Se uma migração for aplicada direto no Supabase (via MCP ou SQL editor, fora do
  fluxo normal do app), ela TEM que ser registrada manualmente na mesma hora com
  `insert into public.migrations (name, aplied_at) values ('0XX_nome.sql', now())`
  — senão o próximo boot tenta rodar de novo. `CREATE POLICY`/`CREATE TABLE` sem
  `IF NOT EXISTS` não é idempotente: a segunda tentativa lança exceção não
  tratada em `post_fork`, mata o worker, gunicorn conta como falha de boot e
  chama `HaltServer` — Render reinicia o container, bate no mesmo erro de novo,
  crash-loop infinito (sintoma visível: site "recarregando" sem parar / 502
  constante). Incidente real: 2026-09-30, migrações 031/032.

## 10. Documentação atualizada a cada rodada de trabalho relevante (diretriz permanente)

- Sempre atualizar o `README.md` e a documentação do projeto (`docs/`) pra não ficar
  desatualizada com o código, a cada rodada de trabalho relevante — prática permanente a
  seguir daqui pra frente em toda sessão futura, não uma tarefa única. (origem: pedido direto
  de Rafa, 2026-09-30)

## 11. Migrações 037+ aplicadas antes do deploy do código que as usa (regra permanente, 2026-10-05; incidente-prevenção registrado 2026-10-06)

- O código da branch de multi-perfil completo depende das migrações `037` (trigger de limite de
  3 perfis), `038` (`profile_id` em 14 tabelas), `039` (remove UNIQUE de
  `shopee_credentials.app_id` e troca o de `credential_checks`), `041` (unicidade de `products` por
  perfil, para o mesmo produto existir em 2 perfis). Toda migração nova que o código
  passa a exigir deve ser aplicada no Supabase **antes** de o deploy dessa versão subir.
- Motivo (fato verificado em `database/migrations/__init__.py` e `gunicorn.conf.py`): o
  `run_migrations()` roda no boot (`post_fork`) e aplicaria as pendentes sozinho, mas uma falha
  ali derruba o worker e entra em crash-loop (ver item 9). Aplicar antes, de forma controlada,
  e conferir a linha na tabela `migrations`, evita descobrir o erro no boot de produção.
- **Procedimento: Aplicar via MCP Supabase + Registrar em `public.migrations`** (2026-10-06):
  - Usar MCP Supabase ou SQL editor web do Supabase para rodar cada migração `.sql` em sequência.
  - Imediatamente após cada migração (ou após o lote), registrar na tabela `migrations`:
    ```sql
    INSERT INTO public.migrations (name, aplied_at) 
    VALUES ('037_create_profile_limit_trigger.sql', NOW()),
           ('038_add_profile_id_to_tables.sql', NOW()),
           -- etc., ordenado como em database/migrations/
    ```
  - Verificar idempotência: `SELECT * FROM public.migrations WHERE name LIKE '03%'` deve listar 6 linhas (037-042).
  - Conferir backfill: `SELECT DISTINCT profile_id FROM products LIMIT 5` e `SELECT COUNT(*) FROM shopee_credentials WHERE profile_id IS NULL` devem estar OK.
- **Risco conhecido — Incidente-prevenção 2026-10-06**: Código de produção **antigo** (sem este PR #10) usa `upsert on_conflict (product_id, user_id)` no endpoint `POST /users/me/restore`. A migração 041 muda a unicidade para `(user_id, product_id, coalesce(profile_id))`. Se o código antigo tentar restaurar dados, o restore **falhará com violação de constraint** (o produto do perfil principal vai conflitar com a tentativa do antigo on_conflict). **Solução**: O merge da branch `chore/phase-12-integration` (PR #10) corrige o restore (`POST /users/me/restore`) para respeitar o perfil ativo. **Janela de risco**: Apenas se alguém ativar uma restauração com código de produção antigo após aplicar a migração 041. **Prevenção**: Aplicar migrações antes do deploy do PR #10; garantir que o #10 está em `main` antes de qualquer ativação de restore em produção. A migração é **aditiva, sem rollback** — não há desfazer automático; se o restore falhar, contactar suporte Rafa Studio Produções.
- As migrações 037/038/039/040/041/042 são idempotentes e aditivas (exceto a 039, que só remove/troca
  unicidade, sem alterar dado). Se forem aplicadas fora do app, registrar em `migrations` na
  hora (item 9).
- Escrita em disco local (imagem não-root, usuário `app`, uid 10001): `/shopee_bot/upload`
  (`FLASK_UPLOAD_FOLDER=upload`) e `/shopee_bot/web/media` (mídia de posts na API). O
  `Dockerfile` cria ambos com `chown app` na build. Sem disco persistente do Render o conteúdo
  é efêmero (some a cada deploy). Se montar disco persistente em um desses caminhos, o mount
  nasce `root:root` e esconde o `chown` da imagem: ajustar a permissão no destino (ex.: Shell
  do serviço `chown -R 10001:10001 <mount>` uma vez) ou apontar `FLASK_UPLOAD_FOLDER` para
  um subdiretório criável. Não há variável `RENDER_DISK` lida pelo app.

## Revisão de consistência (2026-10-05)

Itens 2 e 3 conferidos contra `.github/workflows/ci.yml` e `cd.yml` (Python 3.13, flake8
bloqueante, job `frontend`, `workflow_run`, `concurrency`): coerentes. Item 1 continua válido;
o limite de 3 perfis agora também é imposto por trigger no banco (migração 037).

## Referências

- `.github/workflows/ci.yml`, `.github/workflows/cd.yml`
- `git log --oneline` (histórico completo do repositório)
- `api/README.md`, `README.md`
