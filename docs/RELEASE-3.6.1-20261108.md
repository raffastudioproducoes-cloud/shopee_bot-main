# Auto Orbital — release PATCH 3.6.1 em produção (08/11/2026)

**Estado verificado:** `main` atualizada e Render produção **LIVE** no SHA `982a58351bec2cdc42a80ad0aff728e02ae7f648`. `VERSION=3.6.1` no GitHub e no login público; endpoints `/health` e `/api/health/ready` retornaram `{"status":"ok"}`. Homologação autenticada de mídia relatada por Rafa na staging. Não houve postagem externa de teste.

## Autorização e SemVer

- **Autorização expressa de Rafa:** após testar no site staging, confirmou que o MP4 agora é aceito e que o download da imagem original da Shopee funciona; autorizou `merge` à `main`, `versionamento do patch` e atualização geral da documentação.
- **Decisão:** `3.6.0 → 3.6.1` (PATCH SemVer). Corrige rejeição indevida de MP4 válido e melhora feedback de upload existente, sem introduzir funcionalidade pública incompatível nem alteração de contrato/estrutura de dados.
- **Fonte de versão:** `VERSION=3.6.1` e seção datada de `CHANGELOG.md`. `package.json`/`frontend/package.json` mantêm versões internas próprias, não determinam versão pública.
- **Fluxo autorizado:** bump e changelog em PR para `staging` → CI completo → Render staging LIVE, health/readiness e versão pública → PR `staging` para `main` → gate SemVer e CI → merge → Render produção LIVE no SHA → health/readiness/UI → reconciliação documental no Projeto e Vault.

## Alterações incluídas (sem novidades fora do escopo homologado)

1. MP4 H.264/AAC com caixa `uuid` de topo limitada é aceito no **preflight apenas antes da transcodificação**; FFmpeg reconstrói e sanitizador estrito valida a saída. Nenhum MP4 com `uuid` opaca é persistido.
2. Pipeline unificado para mídia de Produtos e Posts preserva limites de tamanho/formatos e controle de acesso existente.
3. Editor de Produtos usa sombra/skeleton, miniaturas com fallback, progresso circular real de bytes enviados e fase distinta de processamento servidor; acessibilidade e celular.
4. Download autenticado da imagem Shopee já fazia parte da **3.6.0**, não é alteração de código desta PATCH; Rafa reconfirmou seu funcionamento nesta homologação.

## Evidências anteriores à release

- [PR de implementação #360](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/360), [CI #1156](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42520959009) SUCCESS; staging SHA `1489aea4649be85a25eb1571a6baf0575ff8348d`, Render `dep-dbodr38473hc73ah2u00` LIVE.
- [PR documental #361](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/361), CI #1158 SUCCESS; staging SHA `60434168a15b7a2bc736667e95d20fc8a826a667`, Render `dep-dbodui142hec73daqo8g` LIVE, `/health` e `/api/health/ready` `status:ok`.
- Testes locais da implementação: **1.308 API PASS**, **99 frontend PASS**, TypeScript/build PASS; MP4 real 3.901.039→1.272.047 bytes, sanitizado; arquivos originais não incluídos no Git.
- [Vault #46](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/46-MP4-Upload-Progresso-2026-11-08.md), integrado via [PR #84](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/84).

## Portões desta release — resultados observados

- [x] [PR release #362](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/362), [CI #1160](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42522365231) SUCCESS; merge staging `0d794a98d07455896366b226a3d642890eb10c7e`. Render staging `dep-dboe38e8bjmc73b4pek0` **LIVE** no SHA exato; `/health`, `/api/health/ready` `status:ok`; login mostra **3.6.1**.
- [x] [PR `staging → main` #363](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/363), [CI #1162](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42522674144) SUCCESS e [SemVer #10](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42522674051) SUCCESS; merge `main` `982a58351bec2cdc42a80ad0aff728e02ae7f648`. Histórico diverge por merges documentais, mas **zero diferença de arquivos** entre `main` e `staging` no gate pós-promoção.
- [x] Render produção `shopee-bot` deploy `dep-dboe4uvb9u1s73dinre0` **LIVE** no commit `982a58351bec2cdc42a80ad0aff728e02ae7f648`. Navegador: `/health` e `/api/health/ready` `{"status":"ok"}`; login e splash exibem **3.6.1**. Logs de nível erro consultados a partir do deploy retornaram vazios. Métricas HTTP p95 ainda sem amostras suficientes no intervalo.
- [x] Documentação final espelhada no Vault: [PR #85](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/85) merge `2241e9ecedd45c9666da653a36d94524f42e650a`; [documento 47](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/47-Release-Auto-Orbital-3-6-1-2026-11-08.md), TASK, README e Guia Mestre. Este fechamento atualiza os arquivos gerais do Projeto para refletir o estado real de produção.

## Restrições e risco residual

- Sem alterações em Supabase, RLS, DDL, migrations, scheduler, `pg_cron`, `pg_net`, gateway, integração com redes ou postagem real. Não manipular segredos.
- A validação end-to-end autenticada de Rafa foi **relatada pelo proprietário**; não há coleta de seu login nem teste de postagem externa pelo agente. Manter monitoramento de erros 4xx/5xx no endpoint de mídia após publicação.
- Problema de saúde transitória observado em um rollout anterior foi resolvido no segundo teste; os deploys staging e produção da release 3.6.1 tiveram prontidão pública confirmada após ficarem LIVE.

**Referência técnica:** [UPLOAD-MP4-PROGRESSO-20261108.md](UPLOAD-MP4-PROGRESSO-20261108.md).
