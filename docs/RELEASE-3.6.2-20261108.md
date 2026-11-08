# Auto Orbital — release PATCH 3.6.2 (08/11/2026)

**Estado verificado:** release PATCH 3.6.2 aprovada por Rafa e publicada na `main` `bf558c644d6f42b28baccf766eff0825e17a1d17`, Render produção `dep-dbofl50ae00c739m8bq0` **LIVE no SHA exato**. `/health` e `/api/health/ready` retornaram `{"status":"ok"}`/HTTP 200, `/login` HTTP 200 e o HTML público contém a versão **3.6.2**. A janela de logs depois do deploy não mostrou novos requests 5xx; houve apenas SIGTERM esperado do worker antigo durante substituição.

## Autorização e versionamento

- **Origem:** captura Android de HTTP 502 na galeria de Produtos; investigação e correção em [contrato técnico](UPLOAD-502-TEMPO-PROCESSAMENTO-20261108.md).
- **Autorização do proprietário:** em 08/11/2026, após a staging passar nos testes, Rafa pediu expressamente: *"Pode mergeado com a main, versionar e documentar, pois passou nos testes!"* O teste real é **relato de Rafa**; os testes e smokes automatizados são evidências independentes.
- **SemVer:** `VERSION=3.6.1 → 3.6.2`, incremento **PATCH** para corrigir um timeout e melhorar o acompanhamento de upload já existente. A seção datada `## [3.6.2] - 2026-11-08` em `CHANGELOG.md` é obrigatória antes de PR para main; não alterar outros arquivos de versão independentes do frontend.
- **Fluxo:** branch de release → PR staging → CI/build/Testes → Render staging LIVE (3.6.2) → PR `staging → main` → CI/gate SemVer → merge → Render produção LIVE → health/readiness/login e logs → fechamento documental Projeto e Vault.

## Conteúdo da release — sem expansão do escopo aprovado

1. Somente `POST /api/products/{id}/media`: timeout upstream de conexão/leitura `(5 s, 180 s)` no proxy Flask; outras APIs continuam em 30 s.
2. Timeout retorna HTTP 504 legível; 502 permanece para falha real de conexão, evitando erro genérico no frontend.
3. Na edição de Produto, anel com percentual **real de bytes enviados**; depois da transferência, cronômetro de tempo real de processamento, avisos graduais, resultado persistente e opção de atualizar galeria, **sem reenvio automático**.
4. Nenhum afrouxamento da sanitização MP4/FFmpeg nem alteração de API comercial, Supabase Storage, RLS, migrations, `pg_cron`, `pg_net`, scheduler, gateway, planos ou publicações externas.

## Evidências anteriores à autorização

- Implementação [PR #366](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/366) / [CI #1168](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42526353791) SUCCESS → staging `33d73d97572ce0ee736d535f1cbfe35a11bb3314`, Render `dep-dboep9qvcj2c739apqug` LIVE.
- Reconciliação documental [PR #367](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/367) / [CI #1170](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42526834571) SUCCESS → staging `c4ecfa349056a8000c8337a87cf420f9907592f0`, Render `dep-dboes3p42hec73dbtvt0` LIVE, `/health`, `/api/health/ready` HTTP 200, sem request 5xx novo na janela consultada.
- Testes locais da correção: **1.308 API**, **34 web**, **33 frontend da área**, **5 SemVer**, build TypeScript/Vite PASS. A execução exploratória da suíte estática total frontend teve falhas históricas fora da seleção oficial de CI, sem atribuição comprovada a este patch.
- Vault pré-release: [registro 48](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/48-Correcao-502-Upload-Tempo-Processamento-2026-11-08.md) e PRs #87/#88.

## Portões da promoção — resultados verificados

- [x] [PR de release para staging #368](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/368), [CI #1172](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42531022247) **SUCCESS** (API, frontend, PostgreSQL) e teste local SemVer 5/5 PASS. Merge staging `13d74a0f871223eea8ef8ea80ec17cdcceeb671f`; `VERSION=3.6.2` confirmado no GitHub.
- [x] Render staging `dep-dbofjam8bjmc73b6gkrg` **LIVE** no SHA `13d74a0`; `/health`, `/api/health/ready` `status:ok` e `/login` HTTP 200. Sem novo request 5xx observado; SIGTERM do worker substituído esperado.
- [x] [PR `staging → main` #369](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/369), [CI #1174](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42531343986) **SUCCESS**, incluindo HTTP staging externo, API, frontend, PostgreSQL; [gate SemVer #12](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42531343998) **SUCCESS**. Merge `main` `bf558c644d6f42b28baccf766eff0825e17a1d17`, sem conflitos.
- [x] Render produção `dep-dbofl50ae00c739m8bq0` **LIVE** no SHA `bf558c6` (08/11/2026, 22:42 UTC); `/health` e `/api/health/ready` HTTP 200 `status:ok`, `/login` HTTP 200 e HTML mostrando 3.6.2. Logs sem requests 5xx novos na janela observada, apenas `SIGTERM` normal do processo antigo às 22:42:32 UTC.
- [x] Comparação pós-release: GitHub `VERSION=3.6.2` em `staging` e `main`, **zero diferença de arquivos** entre branches, mesmo com histórico de commits distinto.
- [ ] Sincronização documental pós-release: Projeto nesta PR documental e espelho Vault (README, Guia Mestre, TASK e release específica) após confirmação do deploy. Não confundir commit documental com nova correção operacional.

## Limites de validação e observabilidade

- O 502 da captura tem causa **provável** bem sustentada pela diferença 30 s versus FFmpeg/Storage, mas não foi correlacionado a request ID/log individual.
- A afirmação de teste do proprietário não inclui registro de tempo exato de transcodificação, performance por aparelho ou todas as falhas de rede; não declarar cobertura total.
- Health público, CI e logs não provam integração real com mídias privadas ou postagem em redes. Monitorar 504/502, memória/CPU e Storage se a ocorrência persistir.
- Este documento não autoriza mudanças de banco, custos, filas, segredos, cron nem paradas de produção.
