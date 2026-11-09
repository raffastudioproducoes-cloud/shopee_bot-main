# Auto Orbital — varredura analítica de cibersegurança (07/11/2026)

**Escopo:** release `3.5.0` publicada no commit de produção `435c80afc0b9f37e6439198a538b1d956155c601`, mesmo conteúdo de código do staging `4970f78049e724e3fdbbf63ed265c58943669126`; frontend React/Vite, borda Flask, API FastAPI, Supabase/PostgreSQL e jobs. Leitura estática de código/configuração/build local e catálogo read-only do Supabase; **sem pentest ativo, enumeração de usuários, exploração externa, mutação SQL ou acesso a segredos/CPF de clientes**. Segurança de APIs externas não foi certificada. Próximas revisões devem seguir o [checklist permanente](SEGURANCA-VARREDURA-CHECKLIST.md).

## Sumário executivo e evidência de cobertura

**Nenhuma exposição crítica foi confirmada nesta varredura limitada.** Seis achados de endurecimento merecem mitigação planejada; o risco mais importante é estrutural: a API tem chave privilegiada para consultar o banco e deve continuar verificando conta/perfil em todos os acessos. As proteções atuais são reais, mas não substituem testes cruzados completos com dois usuários de laboratório.

| Área exigida | Resultado observado | Classificação |
| --- | --- | --- |
| 1. Segredos / `.env` / bundle | `git ls-files` não inclui `.env` privado; apenas `.env-example`. Busca de padrões de chave privada/token nos caminhos da aplicação sem matches; `frontend/dist` local sem `sb_secret_`, `sk_live_`, `SUPABASE_KEY`, `APP_ENCRYPTION_KEY` ou `INTERNAL_API_SECRET`. `frontend/src/lib/api.ts` lê só `VITE_API_BASE`; `frontend/src/main.tsx` lê `VITE_BUILD_SHA`. `api/database.py` inicializa a chave Supabase **no servidor**. Não houve inspeção de versões anteriores de bundles/CDN ou de valores Render/GitHub. | **Sem vazamento confirmado**; risco Crítico caso futuramente comprovado. |
| 2. RLS e políticas Supabase | **63/63 tabelas ordinárias `public` com RLS ativo; nenhuma policy `USING (true)`/`WITH CHECK (true)`** nos 46 registros de `pg_policies`; 17 tabelas sem política são fechadas por padrão. No `storage`, 10/10 tabelas ordinárias possuem RLS. O Advisor retorna `rls_enabled_no_policy`: 17 **INFO**, não tabelas abertas. Funções `SECURITY DEFINER` examinadas não concedem `EXECUTE` a `anon`/`authenticated`. | **Não foi encontrado RLS aberto**; risco residual Alto da chave privilegiada no backend. |
| 3. Login apenas no cliente | `frontend/src/stores/authStore.ts` guarda estado visual em `localStorage`, porém `frontend/src/router.tsx::requireAdmin` reconsulta `authApi.me`; `api/routers/auth.py::get_current_user_id` valida cookie JWT, banco, ID, revogação e versão de senha. `web/routes/api_proxy.py` verifica origem em mutações com cookie. | **Bypass cliente→API não demonstrado**; higiene Média do estado local. |
| 4. IDOR / troca de IDs | `api/profiles.py` centraliza `scope_owner/scope_account`; exemplos em `api/routers/products.py::_get`, `posts.py::_get_post`, `lists.py` e `profiles.py` aplicam `user_id` da sessão. Há helpers internos com queries só por ID (`posts.py::_get_post_by_id_only`, `_get_thread_chain`) que dependem de callsites previamente autorizados; os inspecionados fazem o preflight. | **Risco estrutural Alto**, **IDOR explorável não confirmado**. |
| 5. Rate limiting | `web/limiter.py`/Flask-Limiter e `api/routers/auth.py::_check_login_rate_limit` usam limites, `api/rate_limit_store.py` tem Redis atômico **somente se** `RATELIMIT_STORAGE_URI` configurada; caso contrário há contadores locais. `supabase_auth.py` limita cadastro/login/recuperação; `posts.py::generate_copy` limita geração da IA. A variável real de produção não foi lida para proteger segredos. | **Médio**, endurecimento de consistência multi-instância e orçamento de custo. |
| 6. Painéis ADMIN | `api/routers/admin.py` exige `Depends(users._require_admin)` no prefixo; `api/routers/users.py::_require_admin` consulta papel `ADMIN` **no banco**; outras rotas `/admin/ai` e `/admin/shopee` usam essa dependência. A URL/guard frontend não é a barreira de dados. | **Rota ADMIN sem guard não encontrada** nos módulos amostrados. |
| 7. Injeção / IA / entrada | Não foi encontrado `dangerouslySetInnerHTML`, `innerHTML` ou `shell=True` no frontend/API inspecionados; FFmpeg usa lista de argumentos e limita recursos. Existem **riscos concretos de validação de links** e **instruções misturadas a dados no prompt da IA** (abaixo). | **Médio**; sem execução de script/comando demonstrada. |

## Achados que requerem trabalho

### S-01 — `service_role` no backend exige escopo em todos os caminhos

- **Risco: ALTO (arquitetural, não evidência de vazamento ou IDOR explorado).** A credencial privilegiada pode contornar RLS, e uma consulta que esqueça `.eq('user_id', usuário_da_sessão)` poderia acessar registro de outra conta.
- **Locais:** `api/database.py:22`; `api/profiles.py::scope_owner/scope_account`; `api/routers/posts.py::_get_post_by_id_only` e `_get_thread_chain`; `api/routers/users.py` restore/backup; `api/routers/campaigns.py` e RPCs de campanha.
- **Evidência que reduz risco:** autenticação do cookie e escopo presentes nos endpoints amostrados; 63 tabelas públicas com RLS e 0 permissivas; `get_current_user_id` não usa ID livre do navegador como autenticação.
- **Correção proposta:** (1) criar matriz completa de endpoints + IDs e domínios conta/perfil; (2) fazer helpers de consulta/alteração receberem `user_id` e, quando aplicável, `profile_id` **explicitamente**, eliminando caminhos por ID isolado; (3) testar todos com contas fictícias A/B, incluindo criação, mídia, agenda, campanha, export/restore e chamadas de RPC; (4) revisar funções `SECURITY DEFINER`, `search_path` e grants; (5) estudar uso de JWT Supabase com RLS por usuário para fluxos de menor privilégio, mantendo service role apenas em tarefas administrativas/servidor, com transição compatível e testes antes de DDL; (6) bloquear merges quando matriz BOLA falhar.
- **Critério de aceite:** todos os endpoints que aceitam ID de recurso negam A→B e perfil A→perfil B; consulta direta como `anon`/`authenticated` também é negada, com relatório de testes e sem dados reais.

### S-02 — Links de produto aceitos além da origem Shopee

- **Risco: MÉDIO (integridade de URL/phishing; não houve prova de XSS).** `api/routers/products.py::ProductCreate` exige conteúdo não vazio, mas não valida esquema/host dos campos `original_link`, `commission_link` e `image` na entrada. `create_product` só reconstrói o link de afiliado quando `canonical_product_url(original_link)` devolve Shopee; no **caminho alternativo** aceita o link fornecido. `frontend/src/pages/ProductsPage.tsx` e `CatalogSearchTab.tsx` mostram links dinâmicos em `href`.
- **Correção proposta:** (1) tornar HTTPS e lista de domínios Shopee/redirect autorizado regra **obrigatória** para criação/importação de produtos afiliados, salvo requisito explícito de novas lojas; (2) rejeitar `javascript:`, `data:`, URLs sem host e credenciais embutidas; (3) recomputar sempre o link comercial no backend, não aceitar destino de comissão do cliente; (4) introduzir `safeExternalUrl()` na UI como segunda barreira; (5) testes unitários com URL malformada, homógrafo, fragmentos, redirects e esquema proibido.
- **Critério de aceite:** URLs arbitrárias não entram no banco nem são clicáveis, links legítimos Shopee continuam funcionando e a geração da IA usa só destino canônico da conta.

### S-03 — Prompt injection por texto de produto / contexto anterior

- **Risco: MÉDIO (conteúdo gerado e integridade comercial; sem execução de comando demonstrada).** `api/text_variants.py::build_prompt`, `generate_thread_replies` e `apis/llm.py::_build_prompt` interpolam o `product.name`, preço/link e textos anteriores junto das instruções. Nome/texto malicioso pode tentar alterar as instruções do modelo. Há validação determinística de tamanho/rede e reparo de URL, e o modelo **não recebe ferramenta de shell/SQL**; ainda assim a conformidade semântica não é garantida.
- **Correção proposta:** (1) separar mensagens de instrução de campos não confiáveis e delimitá-los como dados citados/JSON; (2) usar schema rigoroso para saída e verificação de links **exatamente** contra `build_affiliate_link` do dono, não apenas presença de alguma URL; (3) recusar/limpar links externos extras, comandos e HTML; (4) criar corpus de prompt injection PT-BR/inglês, Unicode e dados de catálogo; (5) manter revisão humana e autorização explícita antes de postagem, sem dar ao LLM ações diretas nem credenciais.
- **Critério de aceite:** modelo pode produzir copy, mas não muda rede, destinatário, ID de afiliado, destino, estado de publicação nem executa instrução injetada.

### S-04 — Limites locais não são atômicos entre múltiplas instâncias

- **Risco: MÉDIO (residual/condicional).** `api/rate_limit_store.py` implementa contador Redis, porém retorna a modo em memória sem URI; o Guia Mestre só confirma uma instância Key Value **de staging**, não confirmou URI distribuída na produção. O Render principal está com **uma instância**, reduzindo mas não eliminando descompasso entre workers/restarts. Limite de IA por usuário usa `_check_login_rate_limit` (janela curta), não é a mesma coisa que orçamento diário de custo persistido.
- **Correção proposta:** (1) validar a **presença/saúde, nunca o valor**, de `RATELIMIT_STORAGE_URI` e prefixos segregados por ambiente; (2) testar concorrência/429/503 com fixtures; (3) se crescer a instâncias múltiplas, ativar contador compartilhado **já autorizado** ou usar quotas transacionais Supabase para IA, uploads, recuperação e ações caras; (4) estabelecer teto por conta/dia separado do rate-limit por minuto; (5) registrar métricas de bloqueio sem IP/segredos desnecessários. Não contratar novo Redis/Upstash/WAF sem aprovação.
- **Critério de aceite:** N requisições concorrentes não ultrapassam cota global; falha do limitador nega operação sensível; 429 fica claro sem afetar cron/publicações já autorizadas.

### S-05 — Aviso de senhas vazadas do Supabase Auth

- **Risco: MÉDIO (endurecimento da senha, confirmado pelo Advisor).** `supabase_get_advisors(security)` retornou `auth_leaked_password_protection` **WARN**; a proteção nativa de senhas previamente vazadas é oferecida oficialmente a partir do plano Supabase **Pro**. Não é falha de RLS nem prova de conta comprometida.
- **Correção proposta:** (1) preservar a política de comprimento e a autenticação atual; (2) melhorar checagem local de senhas óbvias/reutilizadas sem fazer log/telemetria da senha; (3) considerar validação k-anonymity no fluxo de cadastro **apenas após análise de privacidade/rede e autorização**; (4) se Rafa autorizar plano pago, reavaliar a opção nativa e custo. Não fazer upgrade silencioso nem enviar senha bruta a serviços externos.
- **Critério de aceite:** testes de senha fraca e recuperação; nenhuma senha em log, cookie, frontend storage ou consulta de terceiros em claro.

### S-06 — Estado de autenticação persistido no navegador

- **Risco: MÉDIO (higiene/UX, sem bypass de API demonstrado).** `frontend/src/stores/authStore.ts` persiste `user`, `isAuthenticated` e campo `accessToken` no `localStorage`. Os callsites atuais de login passam string vazia como `accessToken`; a autorização real consulta sessão via cookie e backend. Um estado adulterado pode causar UI temporariamente incorreta, não demonstrou acesso a dados ADMIN.
- **Correção proposta:** (1) remover `accessToken` do store/persistência definitivamente; (2) tratar estado local apenas como cache de renderização e invalidar após `/auth/me`; (3) adicionar testes de localStorage adulterado/deslogado e de 401/403, nunca persistindo JWT em JavaScript; (4) manter cookies `Secure`/`HttpOnly`/`SameSite` e refresh/revogação server-side.
- **Critério de aceite:** manipular storage não altera permissão no backend nem abre dados, e o usuário não vê painel administrativo sem confirmação da sessão.

## Ações prioritárias e ordem de implantação (plano, **não executadas**)

1. **P1:** contratos de autorização/IDOR (S-01) e validação integral de URLs (S-02), usando testes negativos e ajustes de API. Revisão da separação `service_role` somente com desenho compatível, sem desativar RLS existentes.
2. **P2:** IA com dados não confiáveis + validação pós-modelo (S-03); observabilidade e quota durável dos endpoints caros (S-04), respeitando o Redis/cron existentes.
3. **P2:** endurecimento de senha (S-05) e remoção de estado redundante do navegador (S-06); checar CSP do **Jinja legado** antes de ativar `LEGACY_PANEL_ENABLED=true`, pois `web/__init__.py` usa exceção `unsafe-inline` apenas nesse modo.
4. Para cada correção: branch isolada → teste estático/negativo → CI → PR staging → deploy staging LIVE → teste de dois usuários de laboratório autorizado → PR main (com SemVer apropriado) → CI → Render LIVE → health/logs e atualização deste relatório.

## Notas operacionais e limitações da prova

- Consulta Supabase de 07/11/2026: `pg_class`, `pg_policies`, `has_table_privilege`, `pg_proc` e Advisor; **17 INFO** de RLS sem policy são **negação**, não vazamento. 26 tabelas têm grant SELECT `anon`/`authenticated`, porém RLS com regra `false`; confundir GRANT com acesso efetivo produz falsos positivos. A política permissiva PostgreSQL com expressão `false` **não** libera linhas.
- As consultas estáticas não certificam histórico de Git, todos os endpoints nem configuração efetiva de env/proxy/CDN. A única classe de segredo varrida no artefato foi o `frontend/dist` **local**, não o JS baixado do Render; não documentar `0` como prova absoluta de ausência de segredos.
- O release 3.5.0 foi aprovado por CI, SemVer, deploy e readiness, mas isso **não equivale** a prova de segurança por teste ativo, à aprovação Shopee de publicação nem a revisão independente exigida por terceiros.
- `auth_leaked_password_protection` não deve motivar upgrade financeiro unilateral: [documentação oficial Supabase](https://supabase.com/docs/guides/auth/password-security).

**Fontes primárias para as recomendações:** [RLS e service role](https://supabase.com/docs/guides/database/postgres/row-level-security), [chaves Supabase](https://supabase.com/docs/guides/getting-started/api-keys), [Vite env](https://vite.dev/guide/env-and-mode), [OWASP API1:2023](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/), [OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [OWASP Prompt Injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).


## Status das mitigações (atualizado em 09/11/2026)

| Achado | Estado | Evidência |
| --- | --- | --- |
| S-02 — links fora da Shopee | **Corrigido em staging** (aguarda promoção) | `ProductCreate` valida HTTPS + host Shopee e imagem em CDN Shopee; restore usa o mesmo schema; `safeExternalUrl()` na UI; testes negativos em `tests/api/test_products.py` e `frontend/tests/safe-external-url.test.mjs` |
| S-06 — token no navegador | **Corrigido em staging** (aguarda promoção) | `authStore` sem `accessToken`, `migrate` limpa legado; `frontend/tests/auth-store-no-token.test.mjs` |
| S-01 — escopo por conta | **Parcial** (staging) | Helpers de thread de posts exigem `user_id` (`tests/api/test_s01_post_scope.py`); catraca das 52 rotas com ID (`tests/api/test_s01_id_routes_ratchet.py`). **Pendente:** matriz A/B dinâmica por rota, revisão de `SECURITY DEFINER`/grants e estudo de JWT com RLS |
| S-03 — prompt injection | **Corrigido em staging** (aguarda promoção) | Bloco `<dados>` + regra de dado não confiável; links extras recusados após a geração; `tests/api/test_s03_prompt_injection.py`. Conformidade semântica do modelo não é garantida; segue revisão humana antes de postar |
| S-04, S-05 | Pendentes | Dependem de decisão/custo de Rafa (Redis distribuído; plano Supabase Pro ou checagem de senha vazada) |
