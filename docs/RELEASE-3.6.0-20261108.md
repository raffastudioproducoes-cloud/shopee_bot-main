# Auto Orbital — fechamento da release 3.6.0 (08/11/2026)

**Estado: publicada na `main`, deploy Render LIVE e saúde verificada.** Este documento prevalece sobre as notas históricas de 08/11 que dizem que a personalização ainda está somente em staging. A promoção foi autorizada expressamente por Rafa nesta conversa.

## Decisões e escopo

- **SemVer:** `3.5.0 → 3.6.0` (**MINOR**, funcionalidades novas compatíveis, sem breaking change); `VERSION` é a fonte oficial. Entrada datada em `CHANGELOG.md`.
- **Produtos:** botão de download da imagem principal Shopee via endpoint autenticado, validação de propriedade/hosts HTTPS, limite de tamanho, sanitização de bytes e arquivo privado sem persistência em novo bucket.
- **Descrição de referência:** novas postagens imediatas e recorrentes e novas campanhas/listas passam a herdar `products.description`. Edições manuais ou geração IA posteriores ficam **somente no post ou item da campanha**, sem regravar o catálogo; rascunhos legados preservam seus snapshots; restauração explícita disponível por item.
- **Campanhas:** geração IA por produto individual, persona e proteção contra resposta assíncrona obsoleta. Nenhum envio automático é acionado pela edição.
- **Fora do escopo:** copiar mídias adicionais da galeria de Produtos para posts/campanhas, publicar em redes ou Shopee Vídeo de verdade, efetuar cobranças e ativar novas integrações. A suíte opcional histórica de testes frontend apresenta falhas preexistentes em contratos fora do gate obrigatório (ver limitações).
- **Infraestrutura preservada:** sem SQL/migration, DDL, RLS, mudança em Supabase compartilhado, dois `pg_cron`, `pg_net`, scheduler, tokens, custos, Render plans ou gateway nesta release.

## Trilha de integração, segurança e deploy

| Etapa | Evidência | Resultado |
| --- | --- | --- |
| Código da funcionalidade | [PR #354](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/354), [CI #1144](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42514522631) | Integrado em staging, SUCCESS. |
| Documentação inicial | [PR #355](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/355), CI #1146 | Integrada em staging, SUCCESS. |
| Bump MINOR | [PR #356](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/356), [CI #1148](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42515827161) | `VERSION=3.6.0`, changelog datado; staging SHA `91926bbf2d9de2dc187225d000dc391cee021659`. |
| Gates pós-staging | [CI #1149](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42515963359), smoke HTTP de segurança #204 e ZAP passivo #197 | SUCCESS. |
| Homologação operacional staging | Render `dep-dbocuv942hec73d9lqng` | LIVE no SHA de staging; `/health` e `/api/health/ready` retornaram `{"status":"ok"}`; tela de login exibia 3.6.0. |
| PR para produção | [PR #357](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/357), [CI #1150](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42516149661), [SemVer #8](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42516149625) | Ambos SUCCESS; merge normal `main` SHA `699e81bd18e2b12fc3824f914045627a45844cc2`. |
| CI após merge | [CI push #1151](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42516293479) | SUCCESS no SHA exato da main. |
| Render produção | Serviço `srv-da6vrla6iojc7380a13g`; deploy `dep-dbod0q7b9u1s73dhci7g` | LIVE no SHA exato de `main`, finalizado em `2026-11-08T19:42:25Z`. |
| Smoke em produção | [Site](https://shopee-bot-fj0w.onrender.com/login), [/health](https://shopee-bot-fj0w.onrender.com/health), [/api/health/ready](https://shopee-bot-fj0w.onrender.com/api/health/ready) | Navegador: ambos endpoints `{"status":"ok"}`; splash e rodapé do login exibem **3.6.0**. |
| Estado de branches | `VERSION` lida em `staging` e `main`; comparação GitHub `main...staging` | Ambas **3.6.0**, **zero arquivos diferentes** imediatamente após release; SHAs distintos por merge normal. |

## Testes locais verificados e limites

- **Passaram:** 1.300 testes da API, 208 do scheduler (mais um `xfail` esperado), nove do banco, 27 de segurança/web/CSP, 96 contratos frontend selecionados pela CI, 18 testes específicos da funcionalidade, build Vite/TypeScript, cinco testes do gate SemVer, script de verificação `3.5.0→3.6.0` e `git diff --check`.
- A suíte ampla opcional legada de frontend, fora dos testes selecionados pelo workflow CI, apresentou **23 falhas em 235 testes**. Não foi incluída como sucesso nem foi corrigida sob esta autorização; necessita triagem dedicada se continuar relevante.
- **Não comprovados:** testes com login real da tela Produtos/Campanha em desktop e celular, download contra CDN Shopee real, geração IA com provedor e créditos reais, publicação externa e comportamento comercial de afiliado. CI e health HTTP **não substituem** esses testes. Manter como QA manual pendente de Rafa sem inferir bloqueio da release já autorizada.
- **Não verificados nesta rodada:** logs detalhados de produção e estado read-only dos crons no banco após a release; não houve alteração dos recursos e não se deve afirmar auditoria nova. Render `LIVE`, CI e HTTP foram efetivamente observados.

## Próximas verificações e regras

1. Rafa: validar em sessão autenticada a matriz de [cenários de personalização](PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md#matriz-mínima-de-aceitação-manual) sem provocar post real.
2. Registrar defeitos reproduzidos em tarefa própria; classificar próximo PATCH/MINOR/MAJOR segundo impacto, sempre começando por staging.
3. Atualizar `TASK.md`, Guia Mestre, regras, arquitetura, PRD, DESIGN, README e espelho no Vault **após** o deploy acima, preservando notas históricas como snapshots e evitando declarar integrações externas aprovadas.
