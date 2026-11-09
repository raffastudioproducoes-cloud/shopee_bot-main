# Auto Orbital — seleção de mídias de Produtos nas campanhas e miniaturas MP4

**Data:** 08/11/2026 · **Escopo:** Produtos → Editar; Criar Post → Campanha → Preparar produto  
**Estado:** [PR #372](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/pull/372) integrada à **staging**, [CI #1181](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/42537281662) **SUCCESS**, Render **LIVE** no SHA `755fb84ad9c7fa5cb063ac71d2fab5a07c6926a8` (deploy `dep-dbognenb9u1s73dle02g`). **Release 3.7.0 em produção verificada**: PR #375/CI #1187 + SemVer #14 SUCCESS, merge `a16f569`, Render `dep-dboh27e8bjmc73b7ukfg` LIVE; health/ready/login 200 e HTML 3.7.0, poster privado sem sessão 401, 0 requests 5xx no intervalo observado. QA autenticada em produção não foi repetida pelo agente.  
**SemVer:** release MINOR **3.7.0 publicada em main**, `VERSION=3.7.0`, gate SemVer #14 aprovado, Render produção LIVE no SHA do merge. [Roteiro](RELEASE-3.7.0-20261108.md).

## Decisão do proprietário e requisitos

Rafa aprovou, em 08/11, o plano de reutilização de mídias com dois complementos:

1. O cartão sombreado de upload continua mostrando porcentagem real de transferência até 100%; durante a resposta do servidor, cronômetro e barra **indeterminada discreta** animam o processamento. Após sucesso, o cartão desaparece automaticamente com transição; falhas permanecem para diagnóstico. Nunca atribuir progresso fictício ao FFmpeg.
2. Vídeos já armazenados recebem **miniatura real extraída do MP4** no editor de Produtos e no seletor de campanhas, inclusive para vídeos legados. O vídeo continua reproduzível ao solicitar a prévia, se o navegador suportar o formato.
3. A campanha lista a imagem principal Shopee e as mídias adicionais prontas da galeria permanente do produto, com checkboxes independentes e individuais. Permite Shopee, adicionais, ambos ou nenhum; **não há input de arquivos nem upload na UI da campanha**.
4. A seleção é snapshot de cada item no próprio rascunho; não altera Produto e não inclui automaticamente mídias novas adicionadas depois. A campanha ativada retém cópias privadas próprias, independentes de alterações posteriores na galeria.
5. Arquivos históricos anexados diretamente a campanhas permanecem protegidos/visíveis no rascunho e podem ser removidos explicitamente; a interface não oferece novos uploads por esse fluxo.

## Fluxo técnico

### Produtos / miniaturas privadas

- `GET /products/{id}/media` mantém isolamento por conta, status `ready` e URLs privadas com prazo. Para vídeos acrescenta `thumbnail_url` de mesmo domínio (`/api/products/{id}/media/{uuid}/thumbnail`).
- Novo endpoint de miniatura exige autenticação, valida **produto + mídia + conta**, confere chave restrita `products/{user}/{product}/`, usa imagem JPEG gerada com **FFmpeg restrito e Pillow/sanitizador** a partir do MP4 seguro já armazenado; poster limitado a 2 MiB.
- A miniatura é cacheada em `post-media`, privado, sob chave determinística `.poster.jpg`. O primeiro acesso ao vídeo legado gera poster sem reenvio. Em falha no cache a miniatura já gerada ainda pode ser exibida; exceções não divulgam paths internos. `DELETE` de mídia/produto remove o objeto e poster correspondente. Sem schema novo, bucket novo ou serviço externo.
- Trade-off: o primeiro acesso a um vídeo legado faz leitura do MP4/FFmpeg e pode levar alguns segundos; tentativas subsequentes usam o JPEG cacheado. Se o poster falhar, o frontend mostra ícone/identificação do vídeo, nunca caixa vazia.

### Campanhas / rascunho e ativação

- `CampaignItemSnapshot.selectedProductMediaIds` e `CampaignDraftItem.product_media_ids` são listas opcionais de UUIDs; rascunhos antigos migram na leitura para `[]`. Preservar `use_shopee_image` e `source_image` originais.
- `CampaignPlanner` substitui o input de upload por `CampaignProductMediaSelector`: busca sob demanda o endpoint existente de Produtos quando o item é expandido, mostra miniaturas e seleção individual, mantida na assinatura do rascunho. Checkboxes ficam desabilitados se a política do plano bloquear edição.
- O servidor valida cada UUID como `ready` e pertencente à conta e ao **product_id do item** em `create/update`; valida novamente em ativação para detectar exclusões concorrentes. É proibido confiar só no cliente ou em URL assinada armazenada no rascunho.
- Antes da RPC de reserva, `synchronize_product_media` copia **somente selecionados** no bucket privado, sob `campaigns/{user}/{profile}/{draft}/{product}/linked/`, para a tabela `campaign_draft_media`, usando reserva global de Storage, escopo de perfil, slots e compensação em erro. IDs derivados determinísticos tornam tentativas repetidas idempotentes. Arquivos de campanha legados fora de `/linked/` não são apagados silenciosamente.
- A RPC de reserva já existente faz o snapshot transacional dos anexos privados prontos; o pipeline existente valida compatibilidade por rede, cria cópias imutáveis `campaign-locked/...` e materializa os posts. Se a RPC já reservou a mesma revisão/request_key, o sincronizador não é reexecutado.
- Sem nova SQL migration, mudanças em cron, `pg_net`, filas, OAuth, segredos ou regras de plano. O Supabase é **compartilhado**: os caminhos novos convivem com a main antiga e com todas as mídias históricas.

## Compatibilidade e segurança

- **Zero mídia:** apenas redes que permitem texto; Instagram exige mídia e TikTok exige vídeo. Backend continua validando, sem converter incompatibilidade em sucesso fictício.
- **Conta/perfil:** Produto e galeria são da conta; campanha e suas cópias são do perfil. IDs estrangeiros ou associados a outro produto devem falhar sem copiar bytes.
- **Exclusão concorrente:** mídia removida entre salvar e ativar gera erro claro e exige revisar a escolha, sem fallback silencioso para Shopee. Depois da ativação, os objetos imutáveis continuam independentes da galeria.
- **Legado:** campanhas já salvas com `campaign_draft_media` permanecem legíveis/compatíveis e seus arquivos não são apagados na atualização do rascunho; exclusão segue botão explícito.
- **Custo e limites:** reuso é por referência durante composição; Storage é consumido somente na preparação para ativação e no cache pequeno dos posters. Conserva reserva global/guard de capacidade, limites de produto 5 imagens + 2 vídeos e teto legado 10 anexos por item de campanha. Sem quota acumulada individual.

## Matriz de testes e homologação

- [x] Build TypeScript/Vite e testes de contrato React/Node (resultado exato registrado na TASK).
- [x] `python -m py_compile` para backend modificado; sintaxe aprovada (não substitui pytest).
- [x] Testes pytest de ownership, idempotência, cópia privada, fallback de poster e ativação: **1.314 testes da API PASS** na CI #1181 (o primeiro run #1180 falhou somente no mock novo de Storage, corrigido e revalidado). Testes Python locais não disponíveis por ausência de dependências.
- [x] Staging: PR #372 squash merge `755fb84`, CI #1181 **SUCCESS**, Render `dep-dbognenb9u1s73dle02g` **LIVE** no commit exato; HTTP `/health`, `/ready`, `/login` **200**, endpoint de poster privado **401** sem login; nenhum request **5xx** no período de observação de logs pós-deploy. `main` intacta.
- [ ] QA autenticada de Rafa no Android: foto Shopee isolada, fotos/vídeos do produto, ambos, nenhum; vídeo legado com poster; salvar/reabrir rascunho; processamento maior que 30 s; plano bloqueado; exclusão antes de ativar.
- [ ] Verificar reserva/materialização apenas em alvo de teste autorizado, sem postagem externa involuntária.
- [x] Rafa autorizou a promoção MINOR 3.7.0; CI #1187 e SemVer #14 PASS, PR #375 mergeada a main, Render produção LIVE/HTTP 200/HTML 3.7.0. [Detalhes](RELEASE-3.7.0-20261108.md). [ ] QA autenticada em produção e observação de latência real continuam recomendadas.

**Observação:** o endpoint de miniatura é uma leitura HTTP que pode criar cache derivado privado no primeiro acesso; não é upload do usuário nem publicação. Verificar latência e volume sob uso real antes de propor otimização assíncrona.
