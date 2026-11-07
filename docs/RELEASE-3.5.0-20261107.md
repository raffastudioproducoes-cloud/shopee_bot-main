# Auto Orbital — fechamento da release 3.5.0 (07/11/2026)

**Estado: publicada em produção e verificada.** Esta evidência prevalece sobre as notas cronológicas antigas que descrevem a candidata 3.5.0 como exclusiva de staging.

## Escopo e versionamento

- `VERSION`: **3.4.0 → 3.5.0** (MINOR compatível, funções acumuladas de staging). `CHANGELOG.md` tem seção datada `[3.5.0] - 2026-11-07`.
- **147 arquivos** diferentes entre `main` anterior e staging no gate final; campanhas, Criar Post, Análises, painel de redes, credenciais, perfis, identidade da conta, calendário, CPF, DDI e correções de API/UX. O texto completo das mudanças permanece no `CHANGELOG` e nos contratos específicos.
- O Supabase é **único e compartilhado** pelos dois Render. Migrações 090–094 já estavam registradas antes da promoção; nenhuma DDL foi executada neste ciclo de release. Não houve criação de ambiente, serviço, cron, plano ou gateway.

## Trilha verificável de promoção

| Gate | Evidência e resultado |
| --- | --- |
| Homologação local | `python scripts/check_release_semver.py --base-ref origin/main`: PASS; 1.294 testes de API PASS; 5 testes do gate SemVer PASS; `npm run build`: PASS; `git diff --check`: PASS. |
| Preparação de staging | [PR #350](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/350) mergeada em `staging` SHA `4970f78049e724e3fdbbf63ed265c58943669126`; [CI #1136](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42425292095) SUCCESS. |
| Render staging | `dep-dbnr8dqvcj2c738oi1lg` **LIVE** no SHA de staging acima; `/api/health/ready` HTTP 200, `status=ok`. |
| Promoção de produção | [PR #351](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/351) com [CI #1138](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42425576719) SUCCESS e [SemVer #6](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42425576708) SUCCESS; merge normal em `main` SHA `435c80afc0b9f37e6439198a538b1d956155c601`. |
| Render produção | Serviço `srv-da6vrla6iojc7380a13g`, deploy `dep-dbnr9vq9lscs73ccndpg` **LIVE** no SHA exato de `main`, concluído em `2026-11-07T23:33:09Z`. |
| Smoke em produção | `https://shopee-bot-fj0w.onrender.com/health` e `/api/health/ready`: **HTTP 200**, `{"status":"ok"}` em ambos. |
| Logs | Após início da nova instância, zero logs `error/fatal` no recorte observado desde `23:33:17Z`. Um `SIGTERM` do worker antigo às `23:33:13Z` foi observado durante o rollout e sucedido por inicialização/saúde da nova instância. |
| Consistência Git | `main` e `staging`: `VERSION=3.5.0`; diferença de arquivos **zero** imediatamente após a promoção, embora SHAs de merge sejam distintos. |
| Supabase | Consulta read-only posterior à publicação: somente `auto-orbital-uptime-sample-v1` (`*/12 * * * *`) e `auto-orbital-wake-v1` (`*/2 * * * *`), ambos `active=true`. |

## Limites da homologação

- A CI, a saúde e o deploy não demonstram execução real de campanhas/redes, autorização Shopee Vídeo, comissão de afiliado, autenticação de todos os fluxos em navegador, cobrança nem desempenho de anúncios.
- O gateway de pagamento permanece **não implementado/homologado**; os dados cadastrais apenas preparam o futuro fluxo.
- Um único serviço Render Free não constitui promessa de uptime absoluto. Produção e scheduler não foram pausados deliberadamente.
- A auditoria analítica de segurança desta mesma rodada é **separada** da promoção: [relatório](SEGURANCA-AUDITORIA-20261107.md) e [roteiro reutilizável](SEGURANCA-VARREDURA-CHECKLIST.md). Nenhum pentest ativo foi realizado.

## Governança pós-release

Registrar o fechamento neste repositório e em `Projetos/ShopeeAutoVendas/` do Vault somente **após** as confirmações acima; atualizações somente documentais não alteram `VERSION` nem reexecutam DDL. Novos trabalhos voltam a partir da 3.5.0 e passam por branch, PR staging, CI e PR main.
