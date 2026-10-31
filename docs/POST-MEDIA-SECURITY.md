# Midia de posts: estado e proxima etapa

## Estado verificado em 2026-10-21

- O projeto Supabase `autovendas` tem o bucket privado `post-media`, limite de 50 MB por objeto e MIME permitido para JPEG, PNG, GIF, WebP e MP4. Esta constatacao veio de consulta somente leitura a `storage.buckets`; nao e um teste de upload.
- O endpoint de rascunho limita leitura/tamanho, detecta assinatura real, confere extensao e MIME declarado, sanitiza nome, redecodifica e reencoda imagens sem metadados, e valida a estrutura basica de MP4. O objeto fica no bucket privado e e associado a usuario/perfil.
- A etapa seguinte redecodifica e reencoda MP4 com FFmpeg antes do Storage, aceita so a primeira faixa de video e audio, remove legendas/dados/metadados e limita duracao, dimensoes, tamanho de saida, tempo de execucao e concorrencia. Falha ou binario ausente rejeita o upload. Isto nao e antivirus: o decodificador roda no mesmo container da API e ainda pode conter vulnerabilidades.

## Política de hospedagem (31/10/2026)

Cloudinary e dependências externas de mídia foram retirados do código ativo.
Uploads novos usam exclusivamente o bucket privado `post-media` do Supabase
Storage. Referências históricas a caminhos locais são rejeitadas com orientação
de reenviar o arquivo; não há reupload automático para serviço externo.
A consulta do banco antes da mudança encontrou 1 mídia em `storage://` e
**zero mídias com caminho local legado ou referência a Cloudinary**.
A consulta não substitui uma publicação real pelas redes.

## Risco aberto com upload de video habilitado

O upload continua habilitado na versao 2.7.0 por decisao do produto, inclusive para usuarios comuns. As medidas abaixo ainda nao foram implantadas; a entrega nao deve ser descrita como livre de malware ou isolamento completo. Nenhum servico privado pago foi criado.

1. Provisionar scanner antivirus isolado e atualizado, com limite de CPU/memoria/tempo, sem acesso a segredos, banco ou rede interna. Definir retorno de indisponibilidade como falha fechada.
2. Analisar bytes antes de gravar no Storage; rejeitar amostras positivas e registrar so ID da tentativa e motivo, nunca o conteudo. Usar quarentena inacessivel se for necessaria investigacao.
3. Mover o transcode MP4 ja implementado para processo/container isolado, sem acesso aos segredos/API/banco; manter codecs, limites e falha fechada. Nao servir o arquivo bruto recebido.
4. Cobrir EICAR de teste, arquivo truncado, poliglotas, metadados ativos, bomba de descompressao, timeout, scanner offline e tentativa cruzada entre perfis. Testar upload, URL assinada, exclusao e publicacao em staging.
5. So entao considerar o gate de video apto. Nenhum scanner garante risco zero; atualizar assinatura e dependencias continua sendo rotina operacional.

Nao tornar o bucket publico, nao usar `service_role` no navegador e nao declarar videos como "limpos" apenas pela assinatura MP4.

Referencias: [FFmpeg CLI](https://ffmpeg.org/ffmpeg.html), [ClamAV scanning](https://docs.clamav.net/manual/Usage/Scanning.html).
