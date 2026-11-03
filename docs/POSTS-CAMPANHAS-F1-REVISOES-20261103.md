# Auto Orbital — F1/R12: revisões de posts agendados (03/11/2026)

**Estado:** infraestrutura SQL aplicada no Supabase compartilhado; código na branch `feat/campanhas-listas-20261102`, PR #198 DRAFT, **ainda não implantado** em staging/main. Nenhuma publicação externa executada neste trabalho.

## Contrato aprovado por Rafa

- Pode alterar o texto de posts com agenda recorrente para **ocorrências futuras estritamente após 30 minutos** do momento confirmado no relógio do banco. A exatamente T−30, o slot já está congelado.
- Ocorrência já reivindicada, em execução, publicada, falhada ou de resultado incerto nunca é reescrita. O mesmo `posts.id` continua válido.
- Fotos Shopee e arquivos locais permanecem disponíveis **na criação de posts**. A implementação F1 descrita aqui **ainda não permite** adicionar/remover mídia ou trocar produto em um post já agendado; isso exige armazenamento retido por revisão e QA próprio. Não divulgar como edição completa.
- O agendador legado de staging (5 cron) e o de main/produção (6 agendas) são preservados. Não ativar o despacho central F0 sem rollout e aprovação específicos.

## Implementação técnica em branch

1. `069_post_content_revisions.sql`: nova tabela com `snapshot` JSONB, `effective_after` e escopo `post_id,user_id,profile_id`; RLS sem policy pública. Campos `publish_jobs.scheduled_for`, `content_revision_id` e `content_snapshot` são **opcionais e NULL** nos jobs antigos.
2. `create_future_post_revision`: função `SECURITY INVOKER` executável somente por `service_role`. Valida dono/perfil/post-raiz não imediato, exige agenda futura, bloqueia ausência de ocorrência elegível de data e define `effective_after = clock_timestamp() + 30 minutos`. Faz `SELECT FOR UPDATE` no post para serializar edições entre si. Não escreve em `posts`, `schedulers`, `medias`, `posts_medias` nem na fila antiga.
3. `POST /posts/{id}/future-revisions`: endpoint autenticado e escopado; aceita texto validado por rede, preserva produto original e cópia dos metadados de mídia já armazenados; devolve o marco T+30 e `revision_id`. Bloqueia post imediato/sem agenda, troca de produto e mídia nova neste estágio.
4. `publish_jobs.claim`: ao reivindicar uma ocorrência, seleciona a última revisão elegível pelo horário **original** do slot da chave idempotente, com comparação estrita `slot > effective_after`. Grava snapshot no mesmo UPDATE do claim. Em reexecução, preserva o snapshot já congelado. Reenvio manual usa o conteúdo da ocorrência original mesmo quando ela não tinha revisão; não herda revisões posteriores.
5. `publication_context` + `post_content_snapshot` + `database/posts.py`: aplicam a projeção do texto e das mídias apenas no contexto da tentativa reivindicada, sem mutar o post-base; sem snapshot, o caminho legado permanece igual.
6. Editor de post: usa endpoint novo somente para agendados, exibe a última revisão futura e informa que mídia/produto de agendamentos permanecem inalterados. A criação continua com foto principal Shopee, extras se a API fornecer e uploads PC/celular.

## Auditoria Supabase — 03/11/2026

- Antes da migração: `public.migrations` registrada até 068; `post_content_revisions` não existia; `publish_jobs.content_snapshot` não existia.
- Aplicada SQL da 069 pelo conector Supabase. `public.migrations` recebeu **`069_post_content_revisions.sql`** na mesma operação, evitando reaplicação automática no boot.
- Depois: tabela criada, RLS habilitado, **0 revisões**, **12 publish_jobs**, **11 schedulers** preservados; três campos opcionais presentes; `authenticated` sem SELECT/INSERT na tabela e `anon`/`authenticated` sem EXECUTE da função, `service_role` autorizado.
- `EXPLAIN` sem `ANALYZE` confirmou que o novo `claim` SQL é aceito pelo PostgreSQL e não executou escrita/teste de postagem.
- Não foram modificados usuários, tokens, cron, agenda, estado de jobs, histórico, OAuth, planos, mídia existente ou serviços Render.

## Testes e limites antes de promover

- Novos testes unitários e de contrato mockado: `tests/scheduler/test_post_content_revisions.py`, `tests/api/test_post_future_revision_api.py`, além dos existentes de R12.
- **CI mais recente destes commits ainda não comprovado**; não considerar os testes concluídos até workflow atual verde.
- Não executar publicação real para provar a mudança sem destino explicitamente autorizado. Testar revisão de cron com slot em 29/30/31 minutos, edição consecutiva e concorrência entre claim/edição num ambiente controlado.
- A consulta oficial de galeria Shopee está codificada na mesma branch (`GET /products/{id}/shopee-gallery-probe`) e utiliza credenciais já registradas via backend; no Supabase há **2 conexões Shopee habilitadas** (consulta apenas de contagens, sem expor valores). **Ainda falta executar requisição real autenticada:** a rota não está implantada em staging e a sessão de navegador disponível não está autenticada. Não dizer que faltam chaves ou que a API está quebrada; tampouco afirmar disponibilidade de múltiplas fotos sem resposta oficial.
- A próxima etapa de edição com mídia exige guardar cada novo arquivo no Storage privado por revisão, validar ownership e reter o objeto até que todas as ocorrências que o referenciam estejam resolvidas.
