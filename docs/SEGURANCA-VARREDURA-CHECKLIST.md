# Auto Orbital — checklist permanente de varredura de segurança

**Versão do roteiro: 1.0 — 07/11/2026.** Quando Rafa pedir **“varredura”, “revisão de segurança”, “auditoria de brechas”** ou equivalente, executar este roteiro na versão e ambientes **atuais**, sem assumir que uma auditoria antiga vale para um novo SHA. Este documento é um **plano de verificação** e não autorização para invasão, pentest ativo, consulta a dados de clientes, troca de segredo, alteração de RLS ou interrupção de serviço.

## 0. Identidade, escopo e segurança da própria auditoria

1. Ler `AGENTS.md`, `docs/GUIA-MESTRE-IA.md`, `docs/RULES.md`, `docs/TASK.md` e TASK/Guia do Vault; conferir `VERSION`, `CHANGELOG.md`, `git status`, SHA de `staging` e `main`, checks GitHub e SHA **LIVE** Render.
2. **Stack real** (não pressupor Next.js): React 19/TypeScript/Vite 6 no frontend, Flask como proxy público, FastAPI/Uvicorn no backend, Python/Supabase `service_role`, PostgreSQL, Supabase Auth e Storage, APScheduler/pg_cron. Next.js Server Actions e Middleware só são alternativas se essa arquitetura for migrada por decisão expressa.
3. Supabase **único e compartilhado** por staging/main. Preservar os **dois crons** e o `pg_net`; não executar escrita/DDL, brute force, carga intensa, ZAP ativo, uploads maliciosos, consultas a dados pessoais ou testes de duas contas reais sem autorização específica. Usar catálogos `pg_catalog`, `pg_policies`, Advisor, CI e fixtures isoladas.
4. Nunca copiar valor de chave, segredo, token, cookie, CPF, corpo privado ou identificadores de terceiros para relatório/log/PR/chat. Ao encontrar segredo verdadeiro: registrar somente **categoria, caminho, commit/escopo, evidência redigida** e preparar rotação coordenada.
5. Para cada conclusão anotar: **SHA, data/hora UTC/BRT, ambiente, comando/SQL read-only, escopo, evidência, estado (`confirmado`, `risco estrutural`, `não comprovado`, `não aplicável`), severidade Crítico/Alto/Médio e validação pendente**.

## 1. Segredos no código e no bundle — Gestão de Segredos

- Verificar `git ls-files` de `.env*`, `.pem`, JSON de service accounts, `Dockerfile`, arquivos `.github/workflows/`, build `frontend/dist` e histórico Git. Fazer scanner de padrão **com saída mascarada**; inspecionar `VITE_*`, `import.meta.env`, `NEXT_PUBLIC_*` e `process.env` de acordo com o framework real.
- **Regra:** `VITE_*` é público no bundle. Chave Supabase `service_role`/`sb_secret_*`, `API_SECRET_KEY`, `APP_ENCRYPTION_KEY`, OAuth secrets, `INTERNAL_API_SECRET`, tokens administrativos e URLs com senha de Redis/Postgres nunca aparecem no cliente. `anon`/publishable key pode ser pública **apenas com políticas adequadas**, não equivale à chave de serviço.
- Se confirmado: revogar/rotacionar no provedor e rever sessões, variáveis de Render/GitHub, commits/builds/logs, caches e histórico com plano coordenado; não apagar o histórico do Git sem combinar a migração dos consumidores. Prevenir com Gitleaks/pre-commit, secrets no servidor, teste de bundle e revisão CI.
- Validar: build limpo + scanner sem valores sensíveis + rotas de cliente incapazes de chamar API privilegiada diretamente.

## 2. Supabase RLS / grants / funções — IAM no banco

- Inventariar **todas** as tabelas expostas em `public` (e `storage` pertinente), `pg_class.relrowsecurity`, `pg_policies` (`qual`, `with_check`, roles e permissividade), `has_table_privilege('anon'/'authenticated')`, funções `SECURITY DEFINER` + `EXECUTE` público, `search_path`, views e buckets. Consultar `supabase_get_advisors` segurança/performance. Distinguir **RLS sem policy = negar por padrão** de RLS desligado ou policy `USING (true)`.
- Se um recurso for acessível diretamente por cliente, habilitar RLS e políticas restritivas de `auth.uid()`/conta; testes com `anon`, usuário A e usuário B, para SELECT/INSERT/UPDATE/DELETE. Nunca habilitar política universal `true` para “resolver erro” e nunca mudar DDL em banco compartilhado sem migração aditiva, PR e compatibilidade com `main`.
- **Atenção estrutural:** `service_role` usado pelo backend pode contornar RLS; proteger o backend por sessão/ownership, ou migrar gradualmente certas operações para JWT/RLS com escopo de usuário. `SECURITY DEFINER` deve ter EXECUTE mínimo e `search_path` fixo.

## 3. Autenticação e sessão — defesa no servidor

- Inspecionar `frontend/src/stores/authStore.ts`, `frontend/src/router.tsx`, `api/routers/auth.py`, `api/routers/supabase_auth.py`, `web/routes/api_proxy.py`, logout/revogação, cookies, CSRF, OAuth state/PKCE, cadastro e recuperação.
- Diferenciar `localStorage` **apenas estado visual** de autorização real. Testar com fixtures: sem cookie/token → 401; token expirado/revogado → 401; acesso entre contas → 403/404; role adulterada no browser → backend nega. Todos os fluxos privados devem consultar sessão real e impor dependências FastAPI/Flask server-side.
- Planejar MFA, confirmação de e-mail, política de senha e expiração/rotação sem quebrar os logins existentes nem alterar SMTP sem autorização.

## 4. IDOR / BOLA — todo ID que vem da URL ou do payload

- Enumerar handlers de `/products/{id}`, `/lists/{id}`, `/posts/{id}`, `/profiles/{uuid}`, `/campaigns/{uuid}`, mídias/avatares, insights, agendamentos, credenciais e endpoints administrativos. Inspecionar helpers que fazem `.eq('id', id)` ou SQL por ID sem escopo.
- Exigir `user_id` **derivado da sessão**, nunca do body; validar conta e, quando aplicável, perfil no SELECT **e** UPDATE/DELETE/RPC; manter transação e checagem de ownership em chamadas indiretas, listas e helpers. Não confiar em UUID imprevisível, no frontend nem no RLS quando a chave é de serviço.
- Criar regressões com dois usuários/duas contas/dois perfis **fictícios e isolados**, incluindo requests negativos, concorrência e rollback. Sem autorização, não buscar ID de cliente real para provar exploit.

## 5. Rate limiting, abuso de formulários e custo

- Inventariar login, registro, reset, OAuth callback, convites, formulário cadastral, upload, catálogo, IA `generate-copy`, testes ADMIN, refresh de analytics e publicação. Anotar limite por IP + conta + endpoint, janela, Redis compartilhado versus memória local, comportamento em falha, custos e idempotência.
- Validar com **testes unitários/integração isolados**, não ataques de carga na produção. Ao escalar horizontalmente, memória por worker **não** é quota global: usar contador atômico já implementado em `api/rate_limit_store.py` com Redis/Valkey **se existente/autorizado**, ou limite transacional no PostgreSQL para operações críticas; não contratar Upstash/WAF/Redis novo sem decisão de Rafa.
- Para endpoints caros: quotas duráveis de IA/uploads, teto de tamanho/tokens, timeouts, concurrency, validação de captcha/anti-bot **se a ameaça e a viabilidade estiverem comprovadas**, sem quebrar onboarding. Registrar 429/503, mas não inventar disponibilidade externa.

## 6. Administração e privilégios

- Enumerar rotas `api/routers/admin.py`, `/admin/*` em `api/routers/platform_ai.py`, `platform_shopee.py`, `credentials.py`, `users.py` e `web/routes/*`. Inspecionar dependências de `_require_admin` **no servidor** em cada rota e RPC privilegiada; o guard do TanStack Router é apenas UX.
- Testes negativos: usuário comum com URL ADMIN conhecida, POST direto à API ADMIN, role adulterada no navegador e usuário deslogado → 401/403. Verificar que payloads de status jamais incluem chaves nem tokens.

## 7. Injeção de entrada, UI, SQL, uploads e IA

- `rg` por `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `exec`, `shell=True`, SQL f-string, `cursor.execute`, URL/HTML injetável, `href`/`src` dinâmicos, `subprocess`, serialização de logs, importação remota de imagem, SSRF e upload; revisar código atingido **em contexto**. Preservar CSP/CSRF/proxy Origin, codecs isolados e whitelist de domínios.
- LLM: tratar nome, descrição, URL de produto, textos anteriores, conteúdo externo e respostas do modelo como **dados não confiáveis**. Delimitar conteúdo, usar esquema estruturado, checar saída contra regras determinísticas (links exatos, URLs HTTPS permitidas, texto, limites, fontes e ausência de instruções injetadas). **Nunca** executar comando da IA nem conceder ferramenta/ação sensível só por texto gerado. Geração não deve publicar sem confirmação/validação do fluxo autorizado.
- Validar com corpus de testes maliciosos **em fixtures locais** (HTML, URLs `javascript:`, SQL metacharacters, prompt injection, payload gigante, arquivo inválido, caracteres Unicode), sem atacar provedores ou usuários reais.

## 8. Resultado, plano e próxima varredura

- Reportar primeiro achados **confirmados**, depois riscos arquiteturais e não verificados; em cada item: risco, **arquivo+função/rota**, cenário verificável, impacto, plano passo a passo, critérios de teste e prioridade. Categorias sem achado também precisam de evidência negativa e limites da revisão.
- Priorização: **P0 Crítico** (exposição efetiva de segredo/conta/dado com caminho de abuso); **P1 Alto** (controle de escopo/bypass ou impacto sério reproduzível); **P2 Médio** (endurecimento sem exploit demonstrado). Severidade não decorre automaticamente de palavra-chave `service_role`.
- Nenhuma sugestão deste checklist autoriza mudança em produção. Para implementar: branch isolada → migração aditiva se realmente necessária → testes/CI → staging LIVE → autorização de promoção → PR main → CI → deploy LIVE → saúde/logs → espelhar projeto/Vault.
- Roteiro permanente referenciado por `AGENTS.md`, `docs/TASK.md`, Guia Mestre e Vault. Snapshot inicial: [auditoria 07/11/2026](SEGURANCA-AUDITORIA-20261107.md).

**Referências técnicas primárias:** [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [Supabase chaves API](https://supabase.com/docs/guides/getting-started/api-keys), [Vite variáveis de ambiente](https://vite.dev/guide/env-and-mode), [OWASP API1/BOLA](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/), [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [OWASP Prompt Injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).
