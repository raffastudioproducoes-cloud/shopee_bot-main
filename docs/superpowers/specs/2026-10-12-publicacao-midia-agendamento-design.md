# Design - Publicacao de Midia e Agendamento por Rede

> Origem: requisitos aprovados por Rafa em 2026-10-12.
> Estado: aprovado para implementacao em `staging`. Este documento complementa
> `2026-10-11-composicao-midia-por-rede-design.md`; quando houver conflito,
> este desenho mais recente prevalece.

## Objetivo

Uma pessoa prepara texto, imagens e videos uma unica vez. O sistema calcula a
composicao efetivamente entregue por cada rede escolhida, mostra o resultado
antes do envio e cria/publica somente os destinos compativeis. Uma limitacao
de uma rede nunca cancela os demais destinos.

O objetivo e reduzir trabalho manual sem prometer capacidades que o publicador
real ainda nao entrega. O backend continua sendo a autoridade: a interface
orienta, mas nao decide acesso, posse ou compatibilidade final.

## Regras de produto

1. O texto continua agrupado em abas apenas quando limites por rede exigirem
   variantes diferentes. Midia segue o mesmo principio: uma aba extra so
   aparece quando uma composicao realmente divergir.
2. Uma mesma selecao pode resultar em imagem unica, carrossel, video,
   `text_only` ou `blocked`, sempre por rede.
3. `text_only` so e permitido quando o texto daquela rede e valido e o
   publicador da rede efetivamente aceita publicar texto sem midia. Erro de
   texto nunca pode ser convertido em fallback de midia.
4. `blocked` exclui somente aquela rede do lote e explica o motivo. Se ao
   menos uma rede tiver plano entregavel, a pessoa pode continuar.
5. A interface nunca corta, converte, reordena ou remove arquivo de forma
   silenciosa. Ela mostra o modo final e os avisos antes da confirmacao.
6. Toda midia, preview, post, job e log permanece isolado por `user_id` e
   `profile_id`. Nenhuma referencia de outro perfil, ainda que da mesma conta,
   pode ser usada.
7. A fonte de verdade de midia deixa de ser o disco efemero do Render. O
   arquivo original e metadados seguros ficam em armazenamento duravel; cada
   publicador baixa uma copia temporaria somente quando precisar dela.
8. A capacidade exibida precisa refletir o que esta implementado e testado:
   Threads mantem texto, imagem, video e carrossel; Facebook e Instagram so
   passam a anunciar modos adicionais depois de cada publicador correspondente;
   X so anuncia midia depois de upload OAuth com `media.write`; TikTok foto
   exige Creator Info e URL em dominio/prefixo verificado.
9. `Publicar agora` cria os recursos necessarios e dispara a publicacao assim
   que o upload terminar. O historico registra o disparo e, depois, o resultado
   real por rede.
10. `Agendar` abre com data e hora locais atuais, usando os controles nativos
    do navegador. `Recorrente` aceita de um a sete dias da semana para a mesma
    hora, sem duplicar o post na interface.
11. O modal inicia redes funcionalmente conectadas prontas para selecao. Uma
    credencial em carregamento mostra estado de carregamento; uma conexao
    ausente, expirada ou com teste falho nao fica habilitada por engano.
12. `Limpar postagem` remove texto, produtos, arquivos temporarios, variantes,
    selecao de redes e agendamento do rascunho sem fechar o modal.

## Contratos

### Capacidade e plano

Cada rede tem duas informacoes distintas: limites da plataforma e modos
entregues pelo publicador atual. O planejador servidor e seu espelho frontend
devolvem, por rede:

```text
network, mode, media_ids, text_variant, warnings, blocked_reason,
effective_capability
```

`mode` e um de `none`, `single_image`, `carousel`, `video`, `text_only` ou
`blocked`. O servidor recalcula o plano no preview, na criacao e antes de
disparar o job.

### Midia duravel e lote

`POST /posts/media` recebe arquivo temporario no escopo do perfil e devolve
somente metadados seguros. `POST /posts/preview-composition` devolve planos sem
criar post. `POST /posts/batch` cria uma cabeca de post por rede entregavel,
gera `group_id` no servidor, vincula somente as midias do plano daquela rede e
cria o job correspondente.

Arquivos temporarios expiram e sao removidos apenas quando nao possuem vinculo
em `posts_medias`; arquivos confirmados so somem por exclusao autorizada do
post/usuario. O endpoint legado de upload para post existente continua como
adaptador de edicao ate sua substituicao posterior.

### Agendamento

O schema preserva `day_of_week` legado e acrescenta `days_of_week` para os
novos jobs recorrentes. A API usa uma lista ordenada sem repeticao de inteiros
de 0 (domingo) a 6 (sabado). O scheduler converte a lista para a expressao do
APScheduler. Jobs antigos seguem funcionando com o campo original.

## Experiencia no modal

Ao abrir, as credenciais do perfil ativo ja foram consultadas. Cada botao de
rede tem estado de conexao independente do rascunho. Apos alterar texto,
produtos ou midia, o resumo por rede muda para: “sera enviado com ...”,
“sera enviado somente com texto” ou “nao sera enviado”, junto do motivo.

O botao de acao usa `Publicar agora`, `Agendar` ou `Agendar recorrencia`.
Uma confirmacao final resume destinos, fallbacks e bloqueios. O resultado do
lote mostra o `mode` efetivo por rede, sem respostas externas brutas ou dados
sensíveis.

## Segurança e observabilidade

- Arquivos sao validados por tamanho, tipo real, nome seguro e limites da rede.
- Nenhuma URL assinada, token, segredo, hash ou corpo bruto de provedor chega
  a logs, atividades ou interface.
- Eventos de clique, preview, criacao, despacho e resultado mantem rede,
  post, job, perfil, modo e erro sanitizado.
- Validacao humana em staging com publicacao visivel continua obrigatoria antes
  de anunciar qualquer modo novo como pronto.

## Entrega e versao

A implementacao ocorre somente em `staging`, em tarefas testaveis. `VERSION`
permanece em `2.1.0` durante todas as etapas. Somente apos todas as tarefas,
revisao integral, testes e validacao de staging a versao sobe uma unica vez
para `2.2.0`; o merge para `main` exige nova aprovacao humana.
