# Criar POST — layout de página e conclusão do experimento de fotos Shopee

**Data:** 03/11/2026 UTC (02/11/2026 BRT)  
**Ambiente:** somente `staging`, branch `fix/criar-post-layout-galeria-conclusao-20261103`  
**Escopo:** aparência da rota `/posts/criar` e decisão R06. Nenhuma mudança de credencial, banco, API, agendador, envio externo ou `main`.

## Diagnóstico visual

A rota exclusiva já existia, porém `PostComposer` aplicava `maxWidth: 900px`, `margin: auto`, fundo elevado, borda, raio e padding de modal. Em viewport desktop o conteúdo aparecia como uma caixa central estreita, destoando das páginas Produtos, Posts e Listas.

## Alteração de interface

- A própria página passa a ocupar a largura útil do `PanelPage`, com cabeçalho e tipografia do design system existente (tokens de cor, espaçamento, borda e tipografia). Sem cartão envolvente do formulário.
- Formulário dividido em regiões funcionais: redes sociais; origem do produto/foto/arquivos; criação e ajuste de texto, limites e agendamento; ações ao final.
- Desktop largo: seleção/mídia e composição/agendamento em duas colunas com divisor discreto. Tablet/celular: uma coluna seguindo a ordem de leitura. Breakpoints 1100/1000/600/380px, larguras fluidas e controles sem overflow horizontal.
- Prévia no desktop ao lado do formulário; em tela menor aparece como seção integrada da página **sem tela escurecida, overlay ou position: fixed**. O compositor de edição de posts existentes não sofre mudança de comportamento.
- Mantidos produto único por post, seleção por lista, check da **foto principal Shopee**, importação de mídia privada, upload de fotos/vídeos do PC/celular, IA, variantes, threads, agendamento Agora/Recorrente 24h e rascunho. Nenhuma alteração de endpoints.

## Experimento Shopee: DECISÃO ENCERRADA

**Pergunta:** os dados retornados ao importar um produto ou o link original do anúncio disponibilizam fotos extras para selecionar automaticamente no Auto Orbital?

**Evidência autenticada anterior:** no PR #200, consulta real `productOfferV2(itemId)` com credencial Shopee ativa, em 3 produtos cadastrados:

| Produto | ID local | Resposta da API |
| --- | ---: | --- |
| Politriz/esmirilhadeira | 34 | `field_unavailable`; apenas `imageUrl` |
| Furadeira Gamma | 33 | `field_unavailable`; apenas `imageUrl` |
| Air Fryer Amvox | 29 | `field_unavailable`; apenas `imageUrl` |

O campo candidato `imageUrls` é rejeitado pelo schema GraphQL. Isso **não** prova que a página de venda tenha somente uma foto.

**Verificação complementar de 03/11 UTC:** conferido o `original_link` salvo do produto #34 (`https://shopee.com.br/product/411693079/22597320196`). A Shopee apresentou `Login Necessário` no navegador de inspeção, sem galeria acessível. A autenticação funcional da Affiliate API no Auto Orbital não equivale a login na interface de compras da Shopee. Não foi pedido novo login, não se burlou a barreira nem se tentou capturar endpoints privados do site.

**Decisão R06 para a integração existente:** **NÃO é possível, com a API de afiliados autenticada atualmente e os links testados, oferecer um seletor confiável de fotos extras**. O seletor experimental **não será ativado nem permanecerá como tarefa indefinida**. O endpoint de diagnóstico read-only pode permanecer sem integração com criação. Foto principal e envio manual de fotos e vídeos **continuam funcionando**.

Isso não é uma afirmação universal sobre todos os produtos da Shopee ou outras integrações autorizadas; reabrir o requisito exige novo canal oficial comprovado e nova decisão de produto, não mais sondagens repetitivas.

## Verificação proporcional

- CI do PR: verificar TypeScript/build e testes automatizados existentes. **Pendente de resultado na abertura do PR.**
- Após deploy LIVE no staging: inspeção visual desktop e viewport mobile; abertura e fechamento da prévia; presença de seleção de produto, foto Shopee e upload. Não criar post real nem enviar mídia.
- Não testar envio social, banco ou cron porque não há alteração dessas rotinas.

## Próxima etapa

Prosseguir com **campanha por lista** como tarefa independente usando a especificação aprovada `docs/superpowers/specs/2026-11-02-campanhas-listas-design.md`, sem fazer merge do PR #198 (DRAFT) e sem promover `main`.
