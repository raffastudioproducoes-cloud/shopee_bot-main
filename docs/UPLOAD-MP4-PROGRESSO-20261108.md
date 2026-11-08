# Auto Orbital — MP4 Google e progresso de upload de Produtos (08/11/2026)

> **Situação atual:** após homologação expressa de Rafa em staging, o lote foi publicado como **PATCH 3.6.1 em produção**, [PR #363](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/363) com CI #1162 e gate SemVer #10 SUCCESS; Render produção `dep-dboe4uvb9u1s73dinre0` LIVE, health/readiness OK e UI 3.6.1. O registro histórico da etapa staging abaixo permanece válido para a data da implantação inicial. [Release e limites](RELEASE-3.6.1-20261108.md) · [Vault doc 47](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/47-Release-Auto-Orbital-3-6-1-2026-11-08.md).

## Origem da ocorrência e diagnóstico reproduzido

- Rafa enviou um MP4 de 3.901.039 bytes gravado/exportado por ferramenta Google em 08/11 e a captura da UI de **Produtos → Editar → Imagens e vídeos do produto** mostrou `Mídia inválida: vídeo inválido: estrutura não permitida`.
- `file` e `ffprobe` confirmaram contêiner **MP4** (`mp42/isom`), vídeo **H.264 High**, 720×1280, 24 fps, 10 s, áudio AAC 48 kHz; nenhum limite de 50 MiB, dimensão ou duração foi ultrapassado. O arquivo enviado não é incorporado à base Git por privacidade/licenciamento.
- Estrutura de topo observada: `ftyp` (24 bytes), `uuid` (31.037 bytes), `moov`, `free` (2 caixas), `mdat`. O validador original de `api/media_sanitizer.py` rejeitava **qualquer** `uuid` antes da transcodificação, ainda que o FFmpeg conseguisse decodificar/reconstruir o conteúdo.
- Reprovação original reproduzida com `sanitize_media_upload`; reconstrução real através de `process_video_upload` aprovada, resultando em MP4 de 1.272.047 bytes, sem persistência externa ou envio ao Supabase.

## Decisão e implementação

1. **Não remover a proteção no Storage:** `sanitize_media_upload` e `_validate_video_boxes` continuam rejeitando `uuid` no arquivo que será persistido. Proibido simplesmente adicionar `uuid` à allowlist final.
2. **Pré-validação limitada:** `validate_video_before_reencoding` só admite até quatro caixas `uuid` de topo válidas, com até 1 MiB no total, após `ftyp`, exigindo `moov`/`mdat`, tamanho coerente, marca MP4 plausível e rejeição de `uuid` aninhado/caixas não aprovadas. Extensão e MIME declarados são checados antes de iniciar FFmpeg.
3. **Reconstrução obrigatória:** `prepare_media_upload` (pipeline comum) passa MP4 aprovado pelo preflight a `process_video_upload` (ffprobe, H.264/AAC, limites, sem metadata/chapters). Em seguida chama **novamente** o sanitizador estrito sobre o arquivo limpo. Se alguma etapa falhar, nenhum byte original vai ao Storage. Imagens seguem pelo sanitizador Pillow habitual. Rotas de upload de Produtos e Posts usam o mesmo pipeline.
4. **Sombras e skeleton:** editor de Produtos apresenta superfície elevada e sombreada que representa o local da nova mídia; efeito shimmer com redução/desativação para `prefers-reduced-motion`; miniaturas já salvas têm sombra, skeleton até o carregamento da prévia, e fallback em erro.
5. **Porcentagem medida:** `XMLHttpRequest.upload.onprogress`, cookie de sessão e multipart padrão do navegador. O anel SVG com texto `N%` e `role=progressbar` mostra **bytes transferidos** (total acumulado ao selecionar vários arquivos), não tempo/processamento fictício. Após o envio, aparece `Transferido; processando mídia…` enquanto a API valida e salva; somente a resposta da API confirma sucesso.

## Segurança, compatibilidade e limites

- Arquivo máximo de 50 MiB; duração/dimensões e rejeição de formatos não MP4 permanecem. Sem CORS relaxado, URL de origem arbitrária, persistência de metadados opacos, bypass de usuário/conta, bucket novo, migration, schema, RLS, cron, pg_net, gateway ou publicação real.
- Percentual não estima processamento remoto; servidores podem levar segundos após 100% e a UI explica esse estado. Numa conexão que não informa total de bytes, o anel permanece no último percentual real (não inventa progresso).
- Mídias existentes são preservadas. O vídeo reenviado terá bytes diferentes, porque a reconstrução retira metadados e reencoda. A aceitação de novas mídias ainda depende de autorização de conta e limites do produto.
- **SemVer:** correção de compatibilidade/UX de fluxo existente = **PATCH 3.6.1**, promovida a `main` **somente após** Rafa homologar staging, autorizar expressamente a promoção e passar o gate SemVer. Regra histórica cumprida em [PR #363](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/363); `VERSION=3.6.1` vigente.

## Testes e aceite

**Espelho documental no Vault:** [documento 46](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/46-MP4-Upload-Progresso-2026-11-08.md), [PR #84](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/pull/84) merge `6d0354d46b1763b613f0237a6ff8a2b76837d5ed`, com TASK, README e Guia Mestre atualizados após deploy staging. Documentação não autoriza produção.

- Backend: testes de preflight estrito/relaxado com uuid (topo, aninhado, tamanho e caixas proibidas), reencodificação, MIME/extensão falsa e rota de Produtos com Supabase fake. Teste separado com o **MP4 real enviado** confirma saída reconstruída de 1.272.047 bytes.
- Frontend: novo contrato Node/CI para XHR, progresso acumulado, anel acessível, skeleton/sombra e movimento reduzido; regressões de carrossel, miniaturas e Produto mantidas. `npm run build` valida TypeScript/Vite.
- [x] [PR #360](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/360) mergeada **apenas em staging** `1489aea4649be85a25eb1571a6baf0575ff8348d`, [CI #1156](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42520959009) SUCCESS (API+lint, frontend+build e PostgreSQL descartável). Testes locais: **1.308 API PASS**, **99 frontend PASS**, `npm run build` PASS, vídeo real reproduziu sanitização de 3.901.039→1.272.047 bytes. Render staging `dep-dbodr38473hc73ah2u00` **LIVE**, vinculado ao SHA exato; `/health` retorna `status:ok`, `/api/health/ready` inicialmente deu indisponibilidade transitória durante a troca de instância, e em novo teste retornou `status:ok`. Login público exibiu versão **3.6.0**. Sem QA autenticada na galeria nem upload externo real.
- [x] **Rafa confirmou que o MP4 passou a funcionar na staging e que o download da imagem Shopee funciona perfeitamente**, aprovando a entrega. A autorização veio do proprietário; o agente não usou suas credenciais para upload autenticado em produção.
- [ ] Testes opcionais adicionais: falhas de rede, cancelamento, carregamento sob conexão lenta e matriz mobile/desktop com múltiplos vídeos. O percentual real e a transcodificação possuem testes automatizados, sem afirmar que todas as condições reais de rede foram exercitadas.
- [x] Somente depois de autorização explícita foi criada a release PATCH 3.6.1 e [PR `staging → main` #363](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/363), CI/SemVer verdes e deploy produção LIVE, `/health`, prontidão e UI 3.6.1 confirmados.

Fonte da regra anterior: [Segurança de mídia de posts](POST-MEDIA-SECURITY.md); [Contrato de Produtos](PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md); [Regras e ambiente](RULES.md).
