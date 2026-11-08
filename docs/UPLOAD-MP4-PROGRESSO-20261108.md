# Auto Orbital — MP4 Google e progresso de upload de Produtos (08/11/2026)

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
- **SemVer:** correção de compatibilidade/UX de fluxo existente = **PATCH candidata 3.6.1** sobre `VERSION=3.6.0` vigente. Não modificar a `main` nem anunciar 3.6.1 liberada antes de Rafa homologar staging, aprovar promoção e executar gate de release.

## Testes e aceite

- Backend: testes de preflight estrito/relaxado com uuid (topo, aninhado, tamanho e caixas proibidas), reencodificação, MIME/extensão falsa e rota de Produtos com Supabase fake. Teste separado com o **MP4 real enviado** confirma saída reconstruída de 1.272.047 bytes.
- Frontend: novo contrato Node/CI para XHR, progresso acumulado, anel acessível, skeleton/sombra e movimento reduzido; regressões de carrossel, miniaturas e Produto mantidas. `npm run build` valida TypeScript/Vite.
- [ ] PR em staging, CI e deploy Render LIVE com health/readiness OK; preencher SHAs/links reais após validação.
- [ ] Rafa confirmar com login a mesma amostra MP4 em Android/desktop, porcentagem de transferência, estado de processamento, reprodução da miniatura e confirmação de persistência; testar imagem e falhas de rede. Teste externo de upload autenticado não executado pelo agente.
- [ ] Somente depois de autorização explícita criar release PATCH 3.6.1 e PR `staging → main`, com novo CI/SemVer e confirmação de deploy. Preservar produção 3.6.0 até essa decisão.

Fonte da regra anterior: [Segurança de mídia de posts](POST-MEDIA-SECURITY.md); [Contrato de Produtos](PRODUTOS-DESCRICOES-CAMPANHAS-20261108.md); [Regras e ambiente](RULES.md).
