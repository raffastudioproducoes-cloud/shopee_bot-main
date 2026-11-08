# Auto Orbital — imagens Shopee e herança de personalização (08/11/2026)

## Escopo autorizado

Rafa autorizou implementar e testar **somente em staging**; a promoção para `main` exige nova aprovação explícita. A referência persistente é o produto salvo em **Produtos**. Publicações isoladas e campanhas podem criar variantes próprias, inclusive com IA, sem alterar essa referência. Sem migrations ou mudanças operacionais de scheduler, `pg_cron`, `pg_net`, Supabase, credenciais ou integrações externas.

## Contratos funcionais

1. **Download de imagem original:** no card expandido da página Produtos, o usuário baixa a imagem principal Shopee em JPG/PNG/WebP para usar em edição externa. O navegador faz GET com `credentials: include` e salva um Blob local; a URL da origem nunca é recebida de parâmetro do navegador nem persistida em um novo bucket. Falhas exibem feedback no card.
2. **Fonte única da descrição padrão:** `products.description` é lida no catálogo e nas listas. A consulta aninhada de `GET /lists` deve incluir `description`; sem isso a tela de campanhas recebe cópia vazia.
3. **Publicar agora ou recorrente:** ao selecionar um produto em novo post, `texts[0]` herda sua descrição salva se ainda não houver texto personalizado. O texto alterado manualmente ou pela IA no compositor prevalece; o produto de origem não é atualizado. Recorrência usa o mesmo formulário e salva a cópia preparada no post.
4. **Campanhas:** uma nova seleção da lista prepara `itemSnapshots[id].copy` com `products.description` e `title` com `products.name`. Mudanças de cada item (incluindo geração IA por persona) ficam no snapshot da campanha. O botão “Usar descrição salva em Produtos” permite recuperar a referência, especialmente em rascunhos antigos. Rascunhos salvos/restaurados mantêm a cópia própria, mesmo vazia, sem atualização automática do catálogo que sobrescreva uma edição anterior.
5. **IA em cada item:** o painel usa `POST /posts/generate-copy` com `description_only=true` e persona escolhida, somente quando o serviço de IA global está disponível. A resposta atualiza apenas o item correspondente se a campanha, lista e conteúdo ainda forem os mesmos desde o início da geração, para não sobrescrever uma edição concorrente. Não executa envio e não altera `products`.

## Segurança e limites

- `GET /products/{id}/image/download` exige cookie httpOnly e confirma propriedade via `scope_account`; produto inexistente/sem imagem recebe 404.
- A origem é restringida a CDNs HTTPS Shopee já utilizadas pelo importador, validando também redirecionamentos. O fluxo limita a leitura a 8 MiB, detecta conteúdo real, reconstrói a imagem via sanitizador e entrega `attachment`, `nosniff`, `private, no-store`.
- Com armazenamento distribuído ativo, downloads são limitados a 30 requisições/minuto por conta. Não há expiração de links públicos novos nem escrita no Supabase Storage.
- Nenhuma mídia é publicada por este download. Imagens/vídeos **adicionais** carregados na galeria privada de Produtos continuam com gerenciamento próprio; não são copiados automaticamente para anexos de campanhas ou publicações neste ajuste. Essa integração precisará de um contrato explícito de seleção/reutilização de mídias e controles de limites por rede, caso seja solicitada.
- O link de comissão continua separado do texto; a descrição de referência em Produtos segue validada em até 280 caracteres ponderados e sem URLs. Uma variante local pode ter regras adicionais por rede na validação do post/campanha.

## Ordem de implementação e testes

1. Consulta de descrição nas listas + snapshot inicial e legado; testes de contrato de API e do reconciliador.
2. Herança no compositor comum de publicação imediata/recorrente e proteção de edições locais; testes da função de precedência.
3. Geração IA no editor da campanha, com prevenção de sobrescrita assíncrona; testes de contrato e build frontend.
4. Download seguro da imagem principal, feedback de UI e testes de autenticação, escopo, formato, conteúdo inválido e rate limit.
5. CI, revisão da staging e QA autenticado em desktop/mobile **sem disparar publicação real**. `main` somente após Rafa aprovar a homologação.

## Evidências e gates

- Testes unitários locais específicos de backend e frontend, `npm run build` e regressões do CI executados antes de PR.
- **A preencher após integração:** PR → staging, CI GitHub, SHA do merge, deploy Render staging LIVE, `/health`, `/api/health/ready`, QA funcional autenticado, pendências.
- Versão vigente: `3.5.0`; funcionalidade compatível candidata à próxima **MINOR 3.6.0** somente quando houver release aprovada. Em staging, registrar no `[Não lançado]` e não mudar `VERSION`.

## Matriz mínima de aceitação manual

| Cenário | Resultado esperado |
| --- | --- |
| Produto salvo com descrição A → novo post agora | Texto A aparece inicialmente; pode ser modificado localmente. |
| Produto salvo com descrição A → novo post recorrente | Mesmo texto A; agenda recebe o snapshot, não regrava o produto. |
| Produto A com descrição → nova campanha da lista | Texto A aparece na edição individual. |
| Gerar texto IA em um item de campanha | Só aquele item muda; a descrição de Produtos e os demais itens não mudam. |
| Editar texto enquanto a IA está processando | Resposta atrasada não substitui a edição humana. |
| Carregar campanha antiga com texto B ou vazio | B/vazio permanece, e o botão de restauração recupera A por escolha. |
| Baixar imagem Shopee | Arquivo local sanitizado, nome compatível com MIME e erro visível quando indisponível. |
| Tentar baixar produto de outra conta | 404 sem consulta ao CDN. |
