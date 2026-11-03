# Auto Orbital — F1 edição futura isolada (02/11/2026 BRT / 03/11 UTC)

## Alcance
Implementação estritamente dedicada à revisão de **texto** dos próximos envios recorrentes, derivada do contrato R12 aprovado por Rafa. Mantém o criador de posts da versão 3.0.0 intacto, bem como foto principal Shopee, uploads de foto/vídeo por PC/celular, agenda, produtos vinculados, redes e histórico.

- Edição é uma versão imutável, não reescrita da publicação anterior.
- O corte é estrito: só ocorrências com horário original **mais de 30 minutos** depois da confirmação no relógio do banco recebem a revisão. No instante exato de 30 minutos, o slot já está congelado.
- Uma ocorrência já `running`, `succeeded`, `failed`, `unknown`, reivindicada ou publicada não é reescrita. Um post recorrente com envio anterior publicado ainda pode ter futuras ocorrências elegíveis.
- Retry conserva snapshot original; sem revisão, usa texto original.
- Edição de mídia/produto de agendamentos **não está incluída** nesta etapa. Exige versionamento e retenção separada de objetos privados para não quebrar publicações antigas.

## Arquitetura

- Migração `069_post_content_revisions.sql` **já aplicada e registrada** no Supabase compartilhado em etapa anterior; inclusão do arquivo no código mantém rastreabilidade e permite implantação limpa em ambientes novos. Nenhuma nova execução de DDL é necessária no estágio atual.
- API `GET /posts/{id}/future-revisions/latest` e `POST /posts/{id}/future-revisions` autenticadas e com checagem de usuário/perfil. O GET existente `/posts/{id}` **não foi alterado**.
- `create_future_post_revision` valida post/agenda em transação e serializa revisões; `publish_jobs.claim` guarda a versão no mesmo UPDATE que assume o job.
- Para crons, o `claim` reconstrói o horário **nominal** do slot a partir do dia da chave e do `schedulers.time`, inclusive virada de meia-noite; não usa o minuto de execução atrasada para decidir o corte. A chave de idempotência e o disparo permanecem inalterados.
- Projeção por `ContextVar` apenas na execução do job, preservando dados permanentes e isolamento entre tentativas.
- Editor de textos fica no modal de detalhes, sob demanda; sem novo caminho de criação ou alteração de `PostsPage`.

## Homologação exigida antes de publicação externa e antes de produção

1. CI de API, segurança, scheduler e frontend; proteção de env staging/main.
2. Contrato de 29, 30 e 31 minutos, continuidade de jobs sem revisão, retry e concorrência edição/claim.
3. QA de staging autenticado somente com registros de teste autorizados e sem disparar posts reais.
4. Verificação no Render e logs; não confundir testes mockados com envio social real.
5. Aprovação separada de Rafa para qualquer promoção a `main`.

O PR #198 continua DRAFT para campanhas, mídia e reformulação de criação. Este recorte não o mescla.
