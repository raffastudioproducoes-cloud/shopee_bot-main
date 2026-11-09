# Auto Orbital 3.8.1 — implantação em staging

**Data:** 09/11/2026 (UTC)  
**Classificação:** PATCH 3.8.0 → 3.8.1  
**Destino:** staging, não produção  
**PR:** [#389](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/389)  
**Merge SHA:** `918af14c0e242a2f732bbfe8c8189eab6c869754`  
**Render deploy:** `dep-dbol68ss728c73ab8r30` — LIVE  
**Migration:** `095_campaign_active_weekday_quota.sql` aplicada em `2026-11-09 05:00:11.28991 UTC`

## Escopo

A PATCH corrige o consumo do limite de dias por weekdays selecionados, o limite dinâmico de data final, o contraste dos dias, as mensagens de bloqueio, a ativação sem salvamento manual, a preservação de edições durante requisições pendentes, a retentativa idempotente de reservas em preparação e a recuperação segura de rascunhos.

## Versionamento e integração

- `VERSION=3.8.1` em staging.
- PR #386 foi integrada antes, por squash SHA `52d8a1a12d9d1c20a0ff8f32072ac250c184b6ab`.
- Branch da implementação criada diretamente da staging atualizada; sem commits atrás.
- PR #389 integrada por squash; SHA final `918af14c0e242a2f732bbfe8c8189eab6c869754`.
- `main` permanece em VERSION 3.8.0 e SHA `78d2d25c7628f7ebe16036e627bb1753a2d1a6c2`.

## CI

CI [#1259](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42564476394) SUCCESS no SHA de código `3a002b341587d432e1ec03c2daa9f10e86ae6a7e`:

- API: 1.332 passed, 9 warnings; lint bloqueante/sintaxe SUCCESS.
- Scheduler: 208 passed, 1 xfailed.
- SemVer: 9 passed.
- Proxy/segurança: 34 passed, 1 warning.
- Frontend: testes Node, TypeScript e build Vite SUCCESS.
- F4E/PostgreSQL descartável: job SUCCESS; migration 095 e ACL testadas.
- Smoke externo staging na CI foi SKIPPED porque a branch ainda não estava implantada.

Os commits posteriores ao SHA testado alteraram somente documentação/metadata; o código implantado corresponde ao código testado.

## Migration 095 e segurança SQL

A migration substitui a função `public.reserve_campaign_f4e` preservando assinatura e validação atômica. Não cria tabelas nem altera dados. Ela foi aplicada pelo boot do serviço staging no Supabase compartilhado.

Registro direto em `public.migrations`:

| Campo | Valor |
|---|---|
| ID interno | 90 |
| Nome | `095_campaign_active_weekday_quota.sql` |
| Aplicada em | 2026-11-09 05:00:11.28991 UTC |

Verificação SQL após aplicação:

| RPC | Owner | EXECUTE service_role | Resultado |
|---|---|---:|---|
| `reserve_campaign_f4e` (v1) | postgres | false | ACL `{postgres=X/postgres}`; corpo conta weekdays |
| `reserve_campaign_networks_f4e` (wrapper v2) | postgres | true | ACL mantém somente owner + service_role |

A RPC legada permanece inacessível diretamente por service_role; a aplicação usa o wrapper SECURITY DEFINER autorizado.

## Render staging

- Serviço: `shopee-bot-staging` (`srv-daukgs17lnhs738tpl50`).
- Deploy: `dep-dbol68ss728c73ab8r30`, status LIVE.
- Commit: `918af14c0e242a2f732bbfe8c8189eab6c869754`.
- Auto deploy: yes.
- Logs confirmam startup da aplicação e scheduler. A instância nova iniciou antes do encerramento da antiga; SIGTERM observado foi do worker antigo durante a troca. Houve um warning transitório de conexão no proxy interno durante o boot.
- Consulta de request logs no intervalo do deploy não trouxe requests.

## Limites de verificação

A ferramenta de navegação não conseguiu acessar os endpoints públicos Render nesta sessão. Portanto, health/readiness/login não foram confirmados por HTTP externo, nem foi possível fazer QA visual/autenticada. O deploy está LIVE e o startup foi observado, mas não afirmar HTTP 200 ou ausência de 5xx sem evidência.

Nenhuma publicação social real foi disparada.

## Produção e risco compartilhado

- Render produção continua no deploy `dep-dbojmmqvcj2c739fjvd0`, SHA `78d2d25c7628f7ebe16036e627bb1753a2d1a6c2`.
- `main` permanece em 3.8.0.
- Nenhum merge/deploy de código em produção foi executado.
- O Supabase é compartilhado. A função SQL da migration 095 já está atualizada no banco também utilizado pelo backend de produção 3.8.0. A assinatura foi preservada e o wrapper permanece autorizado; a promoção do código para produção exige aprovação específica de Rafa.

## Próximos gates

1. Rafa validar visualmente o editor e fluxo autenticado em staging.
2. Executar smoke HTTP externo quando o ambiente de execução permitir acesso ao domínio Render.
3. Só depois avaliar PR de promoção 3.8.1 para main, com nova autorização expressa.