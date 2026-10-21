# Midia de posts: estado e proxima etapa

## Estado verificado em 2026-10-21

- O projeto Supabase `autovendas` tem o bucket privado `post-media`, limite de 50 MB por objeto e MIME permitido para JPEG, PNG, GIF, WebP e MP4. Esta constatacao veio de consulta somente leitura a `storage.buckets`; nao e um teste de upload.
- O endpoint de rascunho limita leitura/tamanho, detecta assinatura real, confere extensao e MIME declarado, sanitiza nome, redecodifica e reencoda imagens sem metadados, e valida a estrutura basica de MP4. O objeto fica no bucket privado e e associado a usuario/perfil.
- MP4 nao e transcodificado nem varrido por antivirus. Dados arbitrarios podem permanecer em `mdat`/`moov`; a validacao atual **nao** comprova ausencia de malware. Tampouco garante que um decodificador de terceiros nao tenha falhas.

## Gate antes de liberar upload de video a usuarios externos

1. Provisionar scanner antivirus isolado e atualizado, com limite de CPU/memoria/tempo, sem acesso a segredos, banco ou rede interna. Definir retorno de indisponibilidade como falha fechada.
2. Analisar bytes antes de gravar no Storage; rejeitar amostras positivas e registrar so ID da tentativa e motivo, nunca o conteudo. Usar quarentena inacessivel se for necessaria investigacao.
3. Transcodificar MP4 em processo isolado para codecs permitidos, sem metadados e com limites de duracao/resolucao; recusar falha do transcode. Nao servir o arquivo bruto recebido.
4. Cobrir EICAR de teste, arquivo truncado, poliglotas, metadados ativos, bomba de descompressao, timeout, scanner offline e tentativa cruzada entre perfis. Testar upload, URL assinada, exclusao e publicacao em staging.
5. So entao considerar o gate de video apto. Nenhum scanner garante risco zero; atualizar assinatura e dependencias continua sendo rotina operacional.

Nao tornar o bucket publico, nao usar `service_role` no navegador e nao declarar videos como "limpos" apenas pela assinatura MP4.
