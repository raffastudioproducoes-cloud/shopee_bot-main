# Auto Orbital — release MINOR 3.7.0 (08/11/2026)

**Autorização:** Rafa, após receber a staging LIVE, concedeu em 08/11/2026: “Pode mergear com a main. Pode promover!”  
**Estado deste registro inicial:** versão preparada para `staging`, **release de produção ainda condicionada a CI/SemVer e Render LIVE**. Não declarar `main` promovida antes de evidências verificadas.

## Escopo homologado

Implementação técnica [PR #372](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/372), registro operacional [PR #373](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/373), [contrato de mídia](CAMPANHA-MIDIAS-PRODUTO-20261108.md).

1. Produtos: percentual circular de bytes reais; após transferência, barra indeterminada para processamento, cronômetro, avisos por fase, sombra/skeleton; ao confirmar, animação e desaparecimento da caixa (sem reenvio automático em falha).
2. Posters JPEG privados extraídos do primeiro quadro de vídeos MP4 já gravados, inclusive legados, com cache autenticado no Storage existente. Miniatura nas visualizações de Produtos e do item de campanha.
3. Campanhas: escolha por produto da foto original Shopee, dos arquivos já salvos em Produtos, de ambos ou de nenhum; sem upload novo na campanha. Fotos/vídeos individuais por UUID e rascunho preservado independentemente da edição base.
4. API revalida conta, produto, status e limite, e na ativação copia somente selecionados para o pipeline privado de anexos; preserva anexos legados e reservas idempotentes.

## Decisão de SemVer

- **De:** `VERSION=3.6.2` (**PATCH** anterior de timeout).
- **Para:** `VERSION=3.7.0` (**MINOR**, nova funcionalidade retrocompatível de seleção de mídia em campanhas); não é PATCH, nem MAJOR.
- `CHANGELOG.md` passa a ter `## [3.7.0] - 2026-11-08` e mantém `## [Não lançado]`.
- O VERSION do frontend permanece derivado do arquivo raiz. Não atualizar números internos independentes sem exigência documental.
- No PR `staging → main`, exigir o workflow “SemVer de release” e `scripts/check_release_semver.py` de `main:VERSION` para `staging:VERSION`.

## Evidências prévias à autorização

- [x] Rafa autorizou em conversa de 08/11/2026 a promoção para `main`.
- [x] PR #372, CI [#1181](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42537281662) **SUCCESS**: 1.314 testes API PASS, 102 frontend PASS, SQL e build PASS.
- [x] PR de evidências #373, CI [#1183](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42537800326) **SUCCESS**.
- [x] Staging final `708a667c2699e6d08414eb5d691481704657d678`, Render `dep-dbogqnivcj2c739cs3sg` **LIVE**, `/health`, `/ready`, `/login` HTTP 200; endpoint de poster sem login HTTP 401, sem requests 5xx observados na janela.
- [x] Projeto e Vault com histórico dos passos: [nota Vault #50](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/50-Midias-Produtos-Campanhas-Poster-MP4-2026-11-08.md).

## Gate de publicação

- [ ] PR release de `release/auto-orbital-3-7-0-20261108` para `staging`: CI verde (API, frontend, SQL), `VERSION=3.7.0` e `CHANGELOG`.
- [ ] Render de `staging` com **commit exato** da release e estado `live` (não apenas trigger).
- [ ] Smoke `/health`, `/ready` e `/login` 200; página HTML com 3.7.0.
- [ ] PR `staging → main`: CI e gate SemVer **SUCCESS**, revisar diff para descartar alterações fora do escopo. Resolver conflitos preservando histórico e controles.
- [ ] Merge `main` após gates, Render produção **live no SHA exato**, smoke HTTP, verificação HTML `3.7.0`, logs sem novos 5xx observados.
- [ ] Registrar SHAs/PRs/execuções/Render, decisões e limitações no Projeto e no Vault somente após a confirmação real.

## Segurança, restrições e rollback

- **Sem DDL/migração nova, alteração de RLS, bucket, secrets, cron, gateway, domínio ou regra de postagem.** Não disparar postagem real em QA técnico.
- A fonte original em `products/{user}/{id}/` continua privada e isolada por conta; `campaign_draft_media` por perfil e `campaign-locked` após reserva. Links assinados não autorizam seleção por si só.
- Posters de vídeos legados são gerados **sob demanda**; a primeira solicitação pode exigir FFmpeg de até 12 s e leitura do MP4. Frente a falha, mostrar fallback. Monitorar a latência do primeiro acesso.
- Uma campanha com muitas mídias pode depender de tempo de Storage na preparação de ativação; observar latência real antes de expandir volume. Retries têm IDs idempotentes; não afirmar que elimina toda disputa concorrente.
- **Rollback:** preferir novo deploy do SHA anterior pela plataforma depois de isolar o problema. Reverter código não apaga arquivos derivados nem reservas já materializadas; não apagar mídia/campanha do usuário automaticamente. Qualquer reversão exige verificação de compatibilidade e acompanhamento de logs.
- O teste autenticado no Android e o aceite de funcionamento são atribuídos ao relato de Rafa; smoke do agente é não autenticado. Não confundir testes técnicos com postagem real.

## Fechamento operacional

*Preencher somente com IDs e resultados observados após a promoção; não inventar CI, deploy ou status.*
