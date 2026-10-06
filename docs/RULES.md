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

Versionamento SemVer (arquivo `VERSION` + `CHANGELOG.md`): a versão só sobe no merge para
`main` — patch = correção, minor = feature compatível, major = mudança grande. O sistema
multi-perfil foi tratado como MAJOR (2.0.0) por decisão do Rafa.

Limitação: a proteção automática de branch NÃO está ativa — o GitHub Free não oferece branch
protection/Rulesets em repositório privado (exige GitHub Pro ou repo público). Por ora a regra
vale por disciplina, até o Rafa decidir. Ver `docs/TASK.md` item 10.13.

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

## 11. Migrações 037+ aplicadas antes do deploy do código que as usa (regra permanente, 2026-10-05)

- O código da branch de multi-perfil completo depende das migrações `037` (trigger de limite de
  3 perfis), `038` (`profile_id` em 14 tabelas) e `039` (remove UNIQUE de
  `shopee_credentials.app_id` e troca o de `credential_checks`). Toda migração nova que o código
  passa a exigir deve ser aplicada no Supabase **antes** de o deploy dessa versão subir.
- Motivo (fato verificado em `database/migrations/__init__.py` e `gunicorn.conf.py`): o
  `run_migrations()` roda no boot (`post_fork`) e aplicaria as pendentes sozinho, mas uma falha
  ali derruba o worker e entra em crash-loop (ver item 9). Aplicar antes, de forma controlada,
  e conferir a linha na tabela `migrations`, evita descobrir o erro no boot de produção.
- As migrações 037/038/039 são idempotentes e aditivas (exceto a 039, que só remove/troca
  unicidade, sem alterar dado). Se forem aplicadas fora do app, registrar em `migrations` na
  hora (item 9).
- Conferir também, ao subir a imagem não-root (`Dockerfile`, usuário `app`), que o disco e a
  permissão de escrita da pasta de upload (`FLASK_UPLOAD_FOLDER`) funcionam no container.

## Revisão de consistência (2026-10-05)

Itens 2 e 3 conferidos contra `.github/workflows/ci.yml` e `cd.yml` (Python 3.13, flake8
bloqueante, job `frontend`, `workflow_run`, `concurrency`): coerentes. Item 1 continua válido;
o limite de 3 perfis agora também é imposto por trigger no banco (migração 037).

## Referências

- `.github/workflows/ci.yml`, `.github/workflows/cd.yml`
- `git log --oneline` (histórico completo do repositório)
- `api/README.md`, `README.md`
