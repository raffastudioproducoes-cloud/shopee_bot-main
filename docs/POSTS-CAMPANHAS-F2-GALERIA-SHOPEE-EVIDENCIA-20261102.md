# Auto Orbital — F2: evidência da galeria de fotos Shopee (02/11/2026)

## Escopo

Decisão técnica relativa a R06, com implantação **somente em branch DRAFT #198**. Nenhum endpoint de terceiro foi chamado com credenciais de usuário, nenhum scraping, publicação externa, migration ou deploy foi realizado nesta análise.

## Fontes primárias e resultado

- Explorador oficial Shopee Affiliate Open API V2: https://open-api.affiliate.shopee.co.id/explorer/v2 — o site oficial confirma a existência da query `productOfferV2`, mas sua visualização pública acessível nesta inspeção **não expôs um schema ou lista de campos verificável** capaz de demonstrar `imageUrls` ou outro campo de galeria.
- Portal brasileiro oficial: https://affiliate.shopee.com.br/open_api — página dependente de JavaScript/login; não permitiu inspeção confiável do schema público nesta sessão.
- Termos oficiais do Programa de Afiliados: https://help.shopee.com.br/portal/10/article/124094-Programa%20de%20Afiliados%20da%20Shopee%20-%20Termos%20e%20Condi%C3%A7%C3%B5es — devem ser respeitados em qualquer aquisição/uso de mídia.
- Termos Shopee para divulgação de vendedor participante: https://help.shopee.com.br/portal/4/article/76443-Programa-de-Afiliados-da-Shopee---Termos-e-Condi%20%C3%A7%C3%B5es — explicitam restrições ao uso automatizado de scraping e apropriação de materiais.

Fontes secundárias mostram `imageUrl` singular em exemplos do `productOfferV2`, porém **não provam nem descartam** outro campo oficial de galeria. Não atribuir a elas autoridade de schema.

## Código atual

`apis/shopee.py`, `api/shopee_catalog.py`, `api/routers/catalog.py` e `api/routers/products.py` consomem `imageUrl` singular; `products.image` é campo legado. `api/routers/posts.py` já tem importação segura da imagem singular para Storage privado, com validação de URL/conteúdo. Bandeja de arquivos locais e `mediaAdapt` suportam múltiplos arquivos em partes do fluxo atual.

## Decisão aguardada de Rafa

1. **Recomendado (temporário):** continuar editor e bandeja de múltiplas imagens próprias/arquivos locais, mantendo coleta automática de outras fotos Shopee **expressamente pendente** até resposta/autorização oficial; nunca anunciar R06 completo. Isso não retira o requisito.
2. **Bloquear F2:** pausar a galeria até validar com suporte Shopee ou schema oficial autenticado, sem acessar segredos ou usar endpoint privado.

Não usar scraping, contorno de autorização, CDN adivinhada ou APIs de vendedor em substituição à API de afiliados sem permissão e contrato adequados. Migração de estrutura e rollout com Supabase compartilhado exigem revisão/autorizações separadas.

## Situação

F1 rota de edição implementada em branch, com backend preservando 409 para posts previamente agendados/publicados. CI do commit de F1 ainda em andamento na hora deste registro. F2 **bloqueada quanto à captura automática**, sem declaração de funcionalidade concluída. TikTok Photo continua no backlog de alta prioridade.
