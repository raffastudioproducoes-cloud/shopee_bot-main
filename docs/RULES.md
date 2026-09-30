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

Branch principal: `master`. Push direto em `master` é a prática adotada — **sem PR** para
grande parte do histórico recente (confirmado no vault, `27-Migracao-App-Unico-OAuth.md`:
"commit já feito local, sem passar por PR (pedido explícito)"). Alguns merges de PR também
existem no histórico (`Merge pull request #5`, `#4`) — os dois fluxos coexistem, decisão é do
dono do projeto por sessão.

## 2. CI (`.github/workflows/ci.yml`)

- Lint com `flake8` sobre `api/` (dois passos: erros de sintaxe `E9,F63,F7,F82` sempre;
  estilo com `--max-line-length=120` tolerante a falha, `|| true`).
- Checagem de sintaxe explícita via `python -m py_compile` nos módulos centrais da API nova.
- Testes: `python -m pytest tests/api --confcutdir=tests/api -q` — **nunca** `pytest` puro
  (quebra `ModuleNotFoundError` em `from api.main import app` sem `-m pytest`).
- `--confcutdir=tests/api` é obrigatório: o `conftest.py` da raiz faz
  `gevent.monkey.patch_all()` (suporte do Flask legado) e trava as threads async do
  `anyio`/`httpx` usadas pelo `TestClient` do FastAPI.
- CI só cobre `tests/api` (API nova) — os testes do Flask legado (`tests/test_auth.py`,
  `tests/test_publish.py`) exigem Postgres local em `localhost:5433` e **não rodam na CI**.

## 3. Deploy

- `cd.yml`: qualquer push em `master` disparra um `curl` no `RENDER_DEPLOY_HOOK_URL` (deploy
  automático). Não há gate de aprovação manual documentado.
- Se o secret não estiver configurado, o job **não falha** — emite `::warning::` e sai com
  `exit 0`. Deploy silenciosamente pulado é uma possibilidade real, não um erro visível.

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

## Referências

- `.github/workflows/ci.yml`, `.github/workflows/cd.yml`
- `git log --oneline` (histórico completo do repositório)
- `api/README.md`, `README.md`
