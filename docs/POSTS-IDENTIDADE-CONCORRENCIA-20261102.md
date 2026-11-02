# Posts — identidade, concorrência e isolamento entre clientes (02/11/2026)

**Escopo:** `staging` apenas. **Produção/`main`:** não alteradas.  
**Segurança:** nenhum envio real para redes sociais foi feito neste trabalho; banco compartilhado auditado só em leitura.

## Pedido e contrato

1. Cada criação de post recebe **um `posts.id` inteiro único**, inclusive se o texto, produto, cliente e segundo de programação forem iguais aos de outro post.
2. Editar preserva `posts.id`; excluir não devolve um número à sequência.
3. A lista mostra o identificador discretamente como `#17` (exemplo), no início de cada post; o modal de detalhes também o identifica.
4. Cada agendamento (`schedulers.id`, UUID) é relacionado àquele post e àquele `user_id`/`profile_id`. Cada ocorrência de envio (`publish_jobs.id`, UUID) referencia post, agenda, conta, perfil e rede, com `idempotency_key` exclusiva por agenda/ocorrência. Não há deduplicação por horário, texto ou produto.
5. A mesma hora/minuto/segundo entre **usuários diferentes, perfis diferentes ou posts diferentes do mesmo usuário** deve criar ocorrências distintas. A idempotência evita *repetir uma mesma ocorrência*, não impede enviar um post diferente.

## Auditoria do esquema existente (Supabase, só SELECT)

- A tabela `posts` já tem `id SERIAL PRIMARY KEY` — a sequência PostgreSQL segue crescendo mesmo após DELETE/rollback. Não foi criada uma segunda numeração nem alterado o esquema compartilhado.
- `schedulers.id` é UUID; `publish_jobs.id` é UUID com `idempotency_key UNIQUE`. `publication_claims` mantém leases por UUID de agenda.
- Amostra lida no banco em 02/11/2026: **5 posts-raiz, 1 parte de thread, 6 schedulers, 8 publish_jobs; maior post ID 28, sequência na posição 29**. IDs podem conter lacunas, propositalmente.
- Verificações cruzadas dos relacionamentos: **0 agendas com usuário/perfil divergentes do post; 0 ocorrências com divergência entre post, agenda, usuário ou perfil; 0 partes de thread ligadas a outro usuário/perfil; 0 IDs duplicados nas agendas**. Essa auditoria fotografa os registros existentes, não substitui um teste de carga.

## Problemas encontrados

| Defeito | Efeito | Correção |
| --- | --- | --- |
| A lista agrupava posts antigos com texto idêntico e criação dentro de 2 minutos, mesmo sem grupo declarado. | Posts independentes podiam parecer um único grupo. | Agrupar apenas por `group_id` explícito; nunca por texto, produto ou timestamp. |
| ID interno invisível ao usuário. | Dificultava distinguir dois posts iguais ou informar suporte. | Mostrar `#posts.id` na esquerda da linha e nos detalhes. |
| A fila tratava `ON CONFLICT (idempotency_key)` sem checar a identidade do item existente. | Em caso de colisão/corrupção, poderia devolver ocorrência de outro usuário/perfil. | Só reutiliza uma ocorrência se agenda, post, usuário, perfil e rede também coincidirem. Caso contrário, erro controlado e sem publicação. |
| Claim de fila verificava somente ID/status. | Uma referência cruzada inconsistente não era barrada na aquisição do worker. | A aquisição atômica exige que agenda, post e ocorrência concordem em usuário, perfil e post; `FOR UPDATE OF job SKIP LOCKED`. |
| Leitura de agenda só pelo UUID, e busca recursiva de filhos sem revalidar dono. | Dados antigos mal vinculados poderiam atravessar a fronteira do cliente/perfil. | JOIN com post conferindo identidade; recursão restrita a dono/perfil, tanto na API nova quanto no leitor legado. |
| Falha na chamada de disparo “Agora” aparecia como falha ao *criar* post. | Usuário podia reenviar e duplicar post já salvo. | Registrar criação concluída separadamente da confirmação de disparo; resultado por rede com `#ID` e aviso para consultar histórico. |

## Testes automatizados adicionados/reforçados

- `tests/scheduler/test_publish_jobs.py`: quatro posts distintos (dois de mesma conta/perfil, um de outra conta, um de outro perfil) programados no mesmo instante geram quatro chaves de ocorrência diferentes; conflito idempotente de outro cliente é rejeitado; claim exige vínculo íntegro.
- `tests/database/test_posts_tenant_scopes.py`: leitura de thread, exclusão de filhos e paginação filtram usuário/perfil em cada nível; edição utiliza `UPDATE ... WHERE id = ... AND user_id = ...`, preservando ID.
- `tests/scheduler/test_profile_scope_scheduler.py`: adapta verificação das novas condições de usuário/perfil da recursão.
- `frontend/tests/posts-composer.test.mjs`: identificador na lista, agrupamento só por `group_id` e tratamento de falha de disparo posterior à criação.

**Limite dos testes:** são verificações de unidade/contrato com banco e APIs simulados; não executam a mesma quantidade de posts contra as plataformas externas. A concorrência real na fila depende das garantias de transação, índice único e `SKIP LOCKED` do PostgreSQL.

## Agendador no staging — bloqueio operacional ainda válido

A mensagem “O agendador de publicações está indisponível neste ambiente…” **não era um erro na identidade dos posts**. A configuração atual desativa o scheduler em staging, enquanto `main`/produção e staging compartilham o **mesmo Supabase e jobstore `apscheduler_jobs`**. A fila `publish_jobs` também é global ao banco.

Ligar o scheduler de staging sem separar banco/fila pode executar agendas do outro ambiente, repetir publicações e criar efeitos reais em contas dos clientes. **Nenhum toggle foi ligado e nenhuma agenda/publicação nova foi enviada.** O preflight de PR #188 continua protegendo o rascunho.

**Para habilitar testes reais de recorrência em staging sem tocar em produção:** providenciar projeto/banco Supabase segregado (avaliar custos/credenciais/migrações) ou aprovar um plano coordenado de particionamento de filas/jobstore em *ambos* os serviços; só então habilitar scheduler exclusivamente para dados/contas de testes. Isso é uma decisão de infraestrutura fora do escopo permitido por “somente staging”. Sem essa separação, é incorreto prometer publicação recorrente funcional no ambiente de estudo.

## Próximos passos de QA (sem envios reais)

1. CI: Python tests da fila, escopos e endpoints, testes frontend, build.
2. Interface staging: confirmar `#ID` por post, inclusive dois posts com mesmo texto; modal exibe o mesmo número.
3. Simular servidor indisponível em “Agora” e confirmar que criação salva não é classificada como erro/necessidade de recriar.
4. Em ambiente isolado *aprovado*: testar horários iguais entre clientes, múltiplos posts idênticos do mesmo cliente, edição preservando ID, exclusão sem reuso, reinício de worker, concorrência entre workers e falhas/timeout/reconciliação da rede.
5. Monitorar Threads real somente com autorização e credenciais de teste; resultados `unknown` exigem conciliação manual, nunca reenvio automático.

## Referências

- `docs/POSTS-SCHEDULER-503-20261102.md` — causa do HTTP 503 e isolamento de staging.
- `database/migrations/053_create_publish_jobs.sql`, `database/publish_jobs.py`, `database/schedulers.py`, `scheduler/__init__.py`, `api/routers/posts.py`.
- Fluxo de identidade: `posts.id` (inteiro crescente) → `schedulers.post_id` (inteiro que aponta para `posts.id`; a agenda tem seu próprio `schedulers.id` UUID) → `publish_jobs.scheduler_id/post_id` (ocorrência de `publish_jobs.id` UUID e chave única por disparo).
