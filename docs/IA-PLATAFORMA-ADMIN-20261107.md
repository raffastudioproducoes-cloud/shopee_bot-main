# IA da plataforma — serviço compartilhado e painel administrativo

**Data:** 07/11/2026
**Escopo:** Auto Orbital, PR #311 integrada em `staging`, release #313 e promoção #314 autorizada por Rafa e publicada em `main` em 07/11.
**SemVer:** funcionalidade compatível **MINOR 3.4.0**, `VERSION=3.4.0` em `main` e `staging`.
**Estado final verificado em 07/11/2026:** **produção e staging LIVE na release 3.4.0.** Após PR #311 CI #1043, PR documental #312 CI #1045 e migração 089 aditiva aplicada/registrada, a PR de release #313 obteve CI #1047 e staging `b5bcbc0` LIVE. A promoção [#314](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/314) passou CI #1049 e SemVer #4; merge `main` `4ca125faf72f58c7d5c7623fc7b2a8bbb215f1b0`, Render produção `dep-dbndgcnb9u1s73cip6mg` LIVE, `/health` e `/api/health/ready` `{"status":"ok"}`, sem erro nível `error` na janela pós-deploy. No Supabase, `production` e `staging` têm Gemini ativo, RLS e restrição de SELECT ao público; os dois cron jobs seguem intocados. **Não houve QA autenticado nem geração real Gemini.** Evidências em `docs/TASK.md` e [RELEASE-3.4.0-20261107.md](RELEASE-3.4.0-20261107.md).

## Contrato aprovado pelo proprietário

- O usuário comum e o ADMIN **não** configuram IA em `/credentials`. Permanecem os cards de redes, Shopee e Shopee Vídeo informativo nas seções de cadastrados/pendentes.
- `/admin/credentials` possui painel exclusivo para IA, com seleção Gemini/OpenAI/Anthropic, chave de API, modelo opcional, salvar/substituir, ativar provedor anteriormente salvo, testar conexão, desconectar e acompanhar status. O segredo **nunca é reexibido**.
- A plataforma custeia e fornece a IA. Produtos/Personalização e Criar Post consultam apenas a disponibilidade do serviço; nenhum cliente envia ou escolhe chave/provedor. O parâmetro legado `provider` em `POST /posts/generate-copy` é aceito mas **ignorado**, preservando clientes antigos.

## Arquitetura

| Componente | Contrato |
|---|---|
| `api/routers/platform_ai.py` | Resolve o provedor **ativo** e decifra a chave somente dentro da API. `GET /ai/status` autenticado retorna apenas `{available: boolean}`. `/admin/ai` (GET/PUT/POST/DELETE) exige papel ADMIN validado no servidor. |
| `public.platform_ai_credentials` | Chaves cifradas com Fernet já usado no backend, organizadas por `(environment, provider)`, com estado do último teste. |
| `public.platform_ai_settings` | Provedor ativo por ambiente (`production` ou `staging`). Não depende do ciclo de vida de nenhum usuário. |
| Migração `089` | `CREATE IF NOT EXISTS`, RLS deny-all, `REVOKE` público/anon/authenticated, acesso do service_role. Copia **sem decifrar** a chave ativa já salva por ADMIN, não por USER, para os dois ambientes. Sem excluir linhas antigas. |
| `database.scheduler_environment.current_environment()` | Resolve origem de deploy pelo branch do Render: staging usa configuração staging; produção usa configuration production; bloqueia branches desconhecidas. |
| `api/routers/credentials.py` | As rotas legadas de IA particular deixam de aceitar leitura/edição/teste (410/403), sem modificar outras credenciais/OAuth. |
| `api/routers/posts.py` | Geração usa exclusivamente `resolve_platform_ai_key()`; mantém limite atual **5 chamadas de geração por usuário a cada 60 s** e checagem de propriedade do produto. |

## Segurança e custos

- Chave permanece no banco cifrada; nunca consta no bundle, armazenamento do navegador, resposta HTTP pública ou logs de teste. Rotas ADMIN exigem autorização backend em todas as operações.
- A consulta pública não revela qual provedor, modelo ou erro de autenticação está em uso. Falta de configuração retorna indisponibilidade segura, sem pedir chave ao cliente.
- Staging e produção compartilham Supabase, mas **não compartilham o provedor ativo/valor editável** após a migração. Um teste no ADMIN da staging não modifica a configuração de produção.
- Limite existente de 5 gerações/minuto por usuário reduz rajadas, mas **não é orçamento financeiro mensal nem cota diária durável**. Antes de abrir a todos os clientes, configurar **limite mensal de gastos** e alertas no projeto de faturamento da Gemini API; monitorar consumo e abuso. Em instâncias múltiplas, validar disponibilidade do rate-limit distribuído, não presumir que limite em memória seja global.
- **A assinatura Google AI Pro não paga automaticamente as chamadas externas da Gemini API**: o uso direto da API possui cobrança/limites do Cloud Billing separados. Ver [Google AI plans](https://ai.google.dev/gemini-api/docs/google-ai-plans?hl=pt-br) e [Gemini API Billing](https://ai.google.dev/gemini-api/docs/billing/).
- Não comprar planos nem ativar cobrança, não enviar posts reais, não modificar pagamentos, `pg_net`, os dois `pg_cron` existentes, OAuth, publicação ou env var de segredo.

## Implantação segura (gates)

1. Testar API, frontend, CSP e migração 089 em ambiente descartável; registrar falhas e ressalvas. Nenhum segredo real usado em teste.
2. Conferir apenas **existência** (não valor) de credencial Gemini ativa de ADMIN. Evidência read-only 07/11: existe 1 registro ativo `gemini` ADMIN; segredo não inspecionado.
3. Aplicar e registrar a migração 089 no Supabase compartilhado **antes do deploy**, conferir duas configurações e RLS, sem alterar credenciais legadas nem crons. Schema aditivo mantém produção 3.3.0 funcional.
4. PR de branch para staging → GitHub Actions verdes → Render staging LIVE e `/health`/`/api/health/ready` 200 → teste ADMIN de consulta de status sem tocar a chave real em produção.
5. Apenas com evidência de staging, preparar release MINOR `3.4.0` em `VERSION`/`CHANGELOG`; PR de `staging` para `main` e gate SemVer; deploy produção sem downtime, health/readiness/logs e paridade documental. Não alegar geração real via provedor sem teste autenticado autorizado.

## Verificações do código

| Verificação | Como repetir |
|---|---|
| Contrato API, ADMIN, tenant e isolamento staging/prod | `python -m pytest tests/api/test_platform_ai_contract.py --confcutdir=tests/api -q` |
| Estado do autoteste, erro, timeout e concorrência | `python -m pytest tests/api/test_credential_autotest.py --confcutdir=tests/api -q` |
| Migração/RLS/cópia do segredo cifrado | `python -m pytest tests/database/test_089_platform_ai_credentials.py --confcutdir=tests/database -q` |
| Remoção da tela comum, manutenção dos controles ADM e disponibilidade | `cd frontend && node --test tests/platform-ai-panel.test.mjs tests/credentials-card-order.test.mjs tests/credentials-sections.test.mjs` |
| Compilação e CSP | `cd frontend && npm run build` e gate Python `tests/web/test_csp_policy.py` |

**Nota de transição:** `public.ai_credentials` legado não é apagado por esta tarefa (histórico e reversibilidade). Nenhum endpoint novo depende dele após a cópia inicial. A remoção definitiva de segredos legados é uma operação sensível futura, mediante política e autorização específicas.
