# Auto Orbital 3.8.0 — Release MINOR em produção

**Data:** 09/11/2026 (BRT)  
**Autorização:** Rafa aprovou expressamente a promoção da staging para main.  
**Repositório:** raffastudioproducoes-cloud/shopee_bot-main  
**PR:** [#382 — release 3.8.0](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/382)  
**Merge:** 5a283baf8aafb843cdb6b576836c0b73ae682784 (squash)  
**Versão:** 3.7.0 → 3.8.0 (**MINOR**)

## 1. Escopo publicado

- Campanhas: seleção global das redes sociais, mantendo a lista existente; sem lojas, modais ou ícones novos.
- Abas de descrição por rede no mesmo espaço da descrição; descrição padrão como fallback e IA aplicada à aba ativa.
- Paginação da lista de produtos em até 10 itens por página, com numeração e navegação.
- Preflight por rede: mídias aceitas/descartadas e motivos, bloqueios de texto, dimensões, duração e tamanho real da imagem Shopee.
- TikTok: consulta Creator Info, limites dinâmicos por conta e upload em chunks sequenciais.
- Ajuda/FAQ e regras atualizadas, incluindo Shopee Vídeo.
- Testes e documentação técnica incorporados.

## 2. Portões e evidências

| Gate | Evidência | Resultado |
|---|---|---|
| CI da PR | [#42554019553](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42554019553) | SUCCESS |
| SemVer da PR | [#42554019572](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42554019572) | SUCCESS |
| Staging externo na PR | Job da PR #382 | SUCCESS |
| CI push main | [#42554207935](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42554207935) | SUCCESS |
| CD GitHub | [#42554322842](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42554322842) | SUCCESS, hook ignorado |
| Render produção | dep-dbojfpcs728c73a9lufg | **LIVE no SHA de merge** |

### Detalhamento do CI push main

- API: **1.323 passed**, 9 warnings.
- Scheduler: **208 passed, 1 xfailed**.
- Testes SemVer: **9 passed**.
- Web/proxy/segurança: **34 passed**, 1 warning.
- Frontend: TypeScript e Vite build SUCCESS.
- F4E/PostgreSQL descartável: job SUCCESS.
- Testes de staging externo são executados na PR staging → main e passaram. No push main, esse job é ignorado por condição do workflow.

## 3. Implantação Render

- Serviço: shopee-bot, ID srv-da6vrla6iojc7380a13g.
- Branch vinculada: main; autoDeploy=yes.
- Deploy: dep-dbojfpcs728c73a9lufg.
- Commit implantado: 5a283baf8aafb843cdb6b576836c0b73ae682784.
- Estado consultado diretamente: **LIVE**.
- Logs de boot: serviço LIVE; Gunicorn/Uvicorn iniciados; startup da aplicação concluído; scheduler iniciado; migrations 001–094 já aplicadas e ignoradas.
- O worker antigo recebeu SIGTERM depois que a nova instância iniciou, compatível com substituição/rolling deploy.

### CD GitHub e deploy automático

O workflow CD #42554322842 terminou SUCCESS, mas o log mostra que RENDER_DEPLOY_HOOK_URL não está configurado e o step saiu com aviso “Deploy ignorado”. Isso **não** foi interpretado como prova de deploy. O serviço Render tem autoDeploy=yes, e o deploy dep-dbojfpcs728c73a9lufg foi confirmado diretamente como LIVE no SHA de merge. A ausência do hook continua sendo uma pendência operacional para corrigir em outro trabalho.

## 4. Integridade e limites

- O diff da promoção não adicionou migrations. No startup, o runtime informou que as migrations 001–094 já estavam aplicadas.
- Nenhuma alteração em schema, RLS, cron/pg_net, gateway, segredos ou serviços externos.
- Nenhuma postagem social real foi disparada.
- O ambiente de execução desta sessão não conseguiu alcançar a URL pública para um smoke HTTP independente de /health, /api/health/ready e /login. Portanto, **não registrar esses endpoints como HTTP 200**. O Render confirmou LIVE e os logs confirmam startup, mas não houve request log no intervalo consultado; não afirmar zero 5xx.
- QA visual/autenticada por Rafa em produção permanece pendente.

## 5. Warnings e follow-ups

1. Runtime/CI: Pydantic reportou que o campo copy de CampaignDraftItem sombreia atributo de BaseModel. Testes passaram, mas revisar nome/alias e compatibilidade de serialização em follow-up.
2. Testes: warnings indicaram chave JWT de 41 bytes abaixo do recomendado para HS384/HS512. Confirmar algoritmo e comprimento exigido no ambiente de teste sem expor ou trocar segredos nesta release.
3. Stack: warnings de depreciação Starlette/httpx, API/framework e Node 20/ações GitHub. Planejar atualização separada.
4. Hook CD Render ausente. Corrigir em tarefa separada, preservando autoDeploy=yes e validando a configuração antes de alterar.

## 6. Rollback

Não houve necessidade de rollback. Se surgir regressão, seguir a política do projeto: diagnosticar primeiro, preferir novo deploy do SHA anterior pela plataforma, preservar estado/dados dos usuários e não reverter migrations/cron/segredos por inferência. Reversão requer avaliação de compatibilidade e evidência.

## 7. Resultado

**Auto Orbital 3.8.0 foi integrada em main e implantada LIVE no Render de produção.** A validação de CI, SemVer, staging externo e estado LIVE do deploy estão comprovados. Smoke HTTP externo e QA autenticada/visual não foram executados nesta sessão e permanecem explicitamente pendentes.
