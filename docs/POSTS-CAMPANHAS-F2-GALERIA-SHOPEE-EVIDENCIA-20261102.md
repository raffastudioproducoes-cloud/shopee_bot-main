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

## Decisão confirmada por Rafa — 02/11/2026

- Seguir com importação manual/seleção de mídia enquanto se comprova a galeria na API autorizada. **Não remover a imagem principal Shopee nem o upload de fotos/vídeos do PC ou celular.**
- Testar ao consultar dados do produto se a API oficial disponibiliza outras imagens. Não inferir resultado real a partir de mock; nenhum scraping ou endpoint privado.
- Com a prova positiva no perfil de testes, as URLs adicionais retornadas podem ser selecionadas na criação do POST; ao importar, o servidor consulta novamente a API oficial e confere pertencimento ao `itemId` antes de baixar e sanitizar para Storage privado.

## Implementação experimental na branch DRAFT #198

- `GET /products/{id}/shopee-gallery-probe`: consulta GraphQL `productOfferV2` assinada com credencial de conta no servidor, tenta campo candidato `imageUrls`, recua a `imageUrl` se o schema rejeitar, filtra CDNs HTTPS e limita quantidade. Não grava dados nem retorna segredo.
- `PostComposer`: seleção visual de extras somente se a consulta retornar URLs, preservando a foto cadastrada e o input `type=file` (fotos/vídeos em PC/mobile).
- `POST /posts/product-image-drafts/{id}`: mantém o corpo vazio para foto principal. Opcional `image_url` só é aceito se a URL HTTPS passou na allowlist e foi confirmada pelo `itemId` em nova consulta assinada; depois reutiliza download limitado/MIME/normalização e bucket privado. URL arbitrária de CDN, mesmo Shopee, **não** é aceita por si só.
- `CreatePostPage`: inclui principal + extras selecionadas + arquivos locais no lote de rascunhos, antes do preview do servidor. Sucesso por rede e limpeza de rascunhos conservados.
- `tests/api/test_shopee_gallery_probe.py` e `frontend/tests/create-post-page.test.mjs`: mocks de resposta múltipla, schema sem campo, SSRF/host, pertencimento ao produto, fallback da foto principal e preservação do file picker.

**Limites e status da evidência:** a API Shopee **real autenticada ainda não foi consultada por esta branch**; portanto não está provado que `imageUrls` existe em produção, nem que arquivos extra são válidos para importação real. A capacidade final depende de consulta autenticada com produto permitido, validação de licença e teste de fluxo completo em staging; não declarar F2 concluída ou deploy realizado. Mock valida o contrato condicional, não a disponibilidade da fonte.

## Situação

F1 rota de edição implementada em branch, com backend preservando 409 para posts previamente agendados/publicados enquanto não há revisão transacional. F2 contém implementação condicional de seleção/importação de extras **em branch DRAFT** e ainda depende de comprovação com API oficial autenticada; a foto principal e uploads locais estão preservados. TikTok Photo continua no backlog de alta prioridade.
