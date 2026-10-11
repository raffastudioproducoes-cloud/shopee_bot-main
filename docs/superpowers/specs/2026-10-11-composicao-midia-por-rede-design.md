# Design - Composicao de Midia por Rede

> Origem: decisao de Rafa em 2026-10-11.
> Estado: aprovado por Rafa em 2026-10-11. A implementacao permanece restrita
> ao staging e segue o plano de implementacao correspondente; nenhuma mudanca
> desta funcionalidade vai para main sem validacao humana posterior.

## 1. Objetivo

Um post multi-rede deve ser tratado como uma composicao: texto, fotos,
carrossel e video sao avaliados separadamente para cada rede escolhida. Uma
incompatibilidade em uma rede nunca cancela a publicacao das outras.

O usuario envia a midia uma vez, escolhe as redes e recebe uma previsao clara
antes de confirmar. Cada rede recebe apenas a composicao que sua API aceita.
Quando uma midia nao for compativel, uma rede com publicacao textual suportada
deve publicar somente o texto valido e exibir aviso explicando a decisao.
Quando a plataforma nao oferecer post textual pela API ou o texto tambem nao
tiver uma variante valida, somente aquela rede fica fora do envio, sem afetar
as demais.

Este comportamento completa o sistema atual de variantes de texto. As abas de
texto e de midia aparecem somente quando existe uma diferenca real entre as
redes selecionadas.

## 2. Regras de produto aprovadas

1. O usuario nao precisa recriar o mesmo arquivo para cada rede.
2. A publicacao e parcial por natureza: uma rede com limite ou formato
   incompativel nao derruba as redes compativeis.
3. Mídia bloqueada gera publicacao apenas de texto naquela rede quando a API
   daquela rede suportar texto sem mídia, com aviso previo e registro posterior
   do motivo. Sem esse modo de API, a rede fica fora com o mesmo aviso.
4. Texto longo usa as variantes por rede ja existentes. Se nao houver texto
   valido para uma rede, ela nao e enviada; o usuario ve isso antes de confirmar.
5. Fotos podem resultar em foto unica ou carrossel conforme as regras da rede.
   Video so vai para redes que o aceitem nas condicoes do arquivo.
6. A selecao de midia e sempre do usuario e perfil ativos. Nunca pode haver
   reutilizacao entre contas ou perfis diferentes.
7. Kwai permanece fora do escopo, pois nao ha API de publicacao confirmada.
8. Suporte completo de video fica registrado como etapa posterior: o planejador
   reconhece compatibilidade, mas upload/processamento de video por cada
   publicador deve ser entregue e testado por rede antes de ser marcado pronto.

## 3. Experiencia de criacao

### 3.1 Biblioteca de composicao

Na criacao do post, o usuario adiciona os arquivos uma vez e define a ordem.
A tela identifica cada item como imagem, GIF ou video por tipo real do arquivo,
nao apenas pela extensao. A selecao de redes continua no mesmo fluxo atual.

O sistema gera um plano por rede ao alterar arquivos, ordem, texto ou redes:

- Rede totalmente compativel: mostra o formato final, por exemplo "carrossel de
  4 fotos" ou "video".
- Rede com midia incompativel: mostra "texto apenas" quando o provedor permite
  texto sem mídia, ou "nao sera enviada" quando o provedor exige mídia; em
  ambos os casos informa o motivo objetivo, como limite, formato ou tamanho.
- Rede com texto incompativel sem variante valida: mostra "nao sera enviada" e
  indica qual limite precisa ser atendido.

Nenhum aviso fica escondido atras do botao de publicar. O resumo fica visivel
na tela e e repetido na confirmacao final.

### 3.2 Abas dinamicas

As abas de texto atuais continuam agrupadas por limite de caracteres. A nova
area de midia usa abas apenas quando dois ou mais grupos de redes precisarem de
composicoes diferentes. Ela nao cria uma aba por rede sem necessidade.

Exemplos:

- Um video valido em todas as redes selecionadas: nenhuma aba extra de midia.
- Quatro fotos quando uma rede aceita carrossel e outra nao: uma aba agrupando
  as redes de carrossel e outra mostrando "texto apenas" para a rede restante.
- Midia aceita com ordens ou limites diferentes: abas agrupadas pela composicao
  efetiva, com selecao e ordem editaveis somente para o grupo afetado.

O usuario pode revisar e ajustar uma composicao proposta. O sistema nunca
silencia uma queda para texto.

O planejador nao corta, reordena nem troca arquivos automaticamente para tentar
forcar compatibilidade. Se a composicao inteira ultrapassar uma regra, a rede
recebe o fallback declarado e o usuario pode editar a aba daquela rede para
propor uma composicao diferente.

## 4. Planejador de compatibilidade

O frontend usa um planejador somente para orientar a pessoa. O backend executa
o mesmo conjunto de regras no momento da criacao e antes da publicacao. Assim,
um pedido manipulado no navegador nao consegue anexar midia proibida a uma
rede.

Para cada rede, o resultado e um `MediaPlan` com:

- `mode`: `none`, `single_image`, `carousel`, `video` ou `text_only`;
- `media_ids`: ativos selecionados naquela rede, em ordem;
- `text_variant`: texto ja validado para a rede;
- `warnings`: motivos de degradacao sem expor segredos ou respostas brutas de
  provedores;
- `blocked_reason`: preenchido somente quando nem mesmo texto valido pode ser
  enviado.

O plano e calculado com os limites centralizados de cada plataforma: contagem,
mistura permitida, formato, peso, dimensoes quando aplicavel e requisitos
especificos de publicacao. Regras que dependem de credencial ou resposta viva
da plataforma sao verificadas novamente pelo publicador antes do envio.

## 5. Dados e API

Hoje o upload em `POST /posts/{id}/media` anexa o arquivo imediatamente ao
primeiro post criado. Isso impede que cada rede tenha sua propria lista sem
criar um post artificial ou duplicar arquivos.

O novo fluxo deve permitir upload temporario com posse em `medias`, mas sem
vinculo em `posts_medias` ate a confirmacao da composicao. Apos a confirmacao,
cada post por rede recebe somente seus `media_ids` no vinculo ja existente.
Isso reaproveita o modelo de dados e evita duplicar arquivos.

Contratos previstos:

- `POST /posts/media` envia um ativo ao escopo `(user_id, profile_id)` e devolve seus
  metadados seguros; nao o publica nem o anexa a um post.
- `POST /posts/preview-composition` recebe texto, redes e ativos e devolve os
  `MediaPlan` calculados, sem gravar post.
- `POST /posts` recebe apenas o plano confirmado por rede; o backend valida
  propriedade, recalcula compatibilidade e cria os posts individuais com um
  unico `group_id`.
- O endpoint legado de upload por post permanece temporariamente como adaptador
  para edicao de posts existentes, sem mudar seu contrato de uma vez.

Ativos temporarios abandonados devem ser removidos por cancelamento explicito e
por limpeza com idade limitada. A limpeza so pode apagar ativos sem
`posts_medias` e sempre filtrados por dono e perfil. Nenhuma rotina pode apagar
midia anexada a outro post.

## 6. Publicacao por plataforma

O publicador de cada rede recebe apenas os ativos listados no `MediaPlan` do
post daquela rede. Ele nunca escolhe arbitrariamente a primeira midia global.

- Threads, Instagram e Facebook devem escolher foto unica, carrossel ou video
  conforme a capacidade oficial da API no momento da implementacao.
- X deve usar o upload oficial OAuth do usuario e o escopo `media.write` para
  ativos aceitos; uma autorizacao antiga sem esse escopo pede reconexao antes
  de anunciar suporte a midia.
- TikTok Photo Direct Post pode usar ate 35 fotos por URLs publicas verificadas
  e exige a consulta de Creator Info e a exibicao das opcoes retornadas ao
  usuario antes da publicacao direta. Video continua pendente de etapa propria.
- Kwai nao entra no planejador de publicacao.

Se uma API recusar um ativo depois da confirmacao, o publicador registra o erro
real da rede. Ele nao troca silenciosamente o conteudo ja confirmado por outro
arquivo; o fallback texto-only e decidido e exibido antes do envio.

## 7. Seguranca, isolamento e observabilidade

- Toda consulta de ativo usa `user_id` e `profile_id` do token, tanto no
  preview quanto na criacao, atualizacao, exclusao e publicacao.
- IDs enviados pelo cliente sao apenas referencias; propriedade e integridade
  sao verificadas no backend antes de anexar qualquer ativo.
- Mensagens para a interface sao legiveis e nao contem token, URL assinada,
  segredo ou corpo bruto de API externa.
- O resultado da execucao registra rede, modo efetivo, aviso de degradacao e
  erro normalizado quando houver, associado ao post e ao perfil corretos.

## 8. Testes e criterios de aceite

1. Testes unitarios do planejador cobrem foto unica, carrossel, video, limites,
   formatos mistos e texto sem variante valida.
2. Testes de API comprovam que um usuario ou perfil nao consegue usar `media_id`
   de outro escopo.
3. Testes de criacao multi-rede provam que cada post recebe apenas os ativos do
   seu plano, preservando ordem e `group_id`.
4. Testes dos publicadores cobrem cada modo suportado e a passagem de texto-only
   quando planejada.
5. Teste visual verifica abas dinamicas, resumo de alertas e que uma rede
   incompativel nao bloqueia o botao de publicar para as demais.
6. Validacao real em staging, com conta autorizada por rede, e obrigatoria antes
   de declarar cada modo pronto. Falta de credito, permissao ou auditoria de
   plataforma deve ser reportada como bloqueio externo, nao como sucesso.

## 9. Fora de escopo desta entrega

- Publicacao pelo Kwai.
- Declarar suporte completo a video sem teste real por plataforma.
- Reescrever o fluxo de credenciais OAuth ou misturar credenciais entre perfis.
- Alterar posts ja publicados para tentar substituir midia retrospectivamente.
