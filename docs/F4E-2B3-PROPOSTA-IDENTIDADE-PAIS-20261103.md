# F4E-2B3 — identidade persistente proposta, sem integração de executor

Data: 03/11/2026. Base inspecionada: staging `379a709f95f9a7ed67701d9bb131a9508ad65a1e`.
Estado: **proposta e testes em PR draft; não implantado**. VERSION=3.0.0.
Nenhuma DDL no Supabase, migration no boot, mudança de main, flag, reserva,
campanha ativa, postagem, OAuth, SMTP, cobrança ou deploy manual.

## Parecer: não é seguro integrar a guarda seletiva agora

Os executores leem schedulers/publish_jobs sem uma origem persistente de
campanha. Reserva e ocorrência F4E-1 não apontam para agenda/job/post.
A tabela de vínculos F4E-2B2 é apenas proposta. O DTO em memória não prova
posse, persistência ou autorização. Ambiente staging e dispatch_mode=central
também não identificam campanha: produção central aceita ambas as origens.

Consultar a tabela ausente em todo claim faria posts legados falharem.
Tratar erro ou ausência de vínculo como “legado autorizado” criaria bypass.
Não foi adicionada consulta, chamada à guarda ou fallback nos executores.

## Melhoria material, exclusivamente na proposta existente

Arquivo único: [SQL F4E2B2](sql-proposals/F4E2B2-INERT-CAMPAIGN-DISPATCH-LINKS.sql),
**fora de database/migrations**.

- Seis índices únicos compostos, todos incluindo a PK do pai: perfil,
  reserva, ocorrência, agenda, post e job. Não limitam a quantidade de
  objetos legados; há custo adicional de escrita/espaço e locks de DDL.
- FKs compostas com ON UPDATE/DELETE RESTRICT impedem que pais vinculados
  troquem conta, perfil, reserva da ocorrência, post, agenda, rede ou
  ambiente. A rede do post também é conferida no INSERT.
- O trigger adquire locks dos pais em ordem explícita: ocorrência, reserva,
  post, perfil, job, agenda; depois valida estado inicial inerte. Isto
  estabiliza a validação inicial, não concede autorização.
- A proteção permanente da identidade vem das FKs nativas, não de SELECT
  num trigger de UPDATE com snapshot antigo. Inclui teste REPEATABLE READ.
- Link continua imutável inclusive para owner; service_role só pode ler,
  sem INSERT/UPDATE/DELETE/TRUNCATE nem EXECUTE no trigger. RLS ativo.
- Status de reserva/ocorrência/job, cancelamento, revisão de dispatch,
  claim, lease, erros e timestamps de execução não entram nas chaves:
  release/cancel/recovery não são confundidos com mudança de identidade.
- UNIQUE(occurrence_id,network) e UNIQUE(publish_job_id) permanecem:
  repetição é rejeitada, não reutilizada silenciosamente. A proposta não
  fornece RPC idempotente de criação e sua reaplicação falha/rollback;
  não a apresentar como migration idempotente pronta.

Não há link criado no Supabase. Apenas o owner do banco descartável insere
fixtures sintéticas para testar o contrato. Adicionar índices/FKs em pais
reais exige autorização de DDL, revisão de locks/custos e compatibilidade
das duas versões; este PR não concede nenhuma dessas autorizações.

## Matriz de integração futura — nenhum ponto abaixo foi alterado

| Fronteira | Arquivos/funções atuais | Proteção ainda exigida |
|---|---|---|
| Criação de intenção | database/schedulers.py: insert; scheduler/__init__.py: _add_job, run_job; api/internal_client.py e web/routes/internal.py | Origem obrigatória persistida atomicamente, sem rota campanha→legado por ausência de vínculo |
| Espelho e agendas vencidas | scheduler/central_reconciler.py: reconcile; database/schedulers.py: list_central_dispatch_jobs, expire_missed_central_dates | Não materializar campanha inerte nem fabricar ocorrência executável no reconciliador |
| Enqueue e claim | database/publish_jobs.py: enqueue, claim; scheduler/__init__.py: execute_publication, _execute_publish_item | Identidade relida/validada na transação, pais estáveis, flag nunca sobrepõe inert |
| Recovery e shutdown | database/publish_jobs.py: recoverable, expire_running, requeue_if_safe; scheduler/__init__.py: drain_publish_jobs | Revalidar antes de requeue/claim; external_started/unknown continuam conservadores |
| Retry manual | database/migrations/062_manual_post_retry.sql: enqueue_manual_post_retry; api/routers/posts.py: retry-unknown | Novo UUID não pode perder origem; não editar migration histórica aplicada; proposta nova deve recusar ou herdar vínculo atomicamente |
| Pré-envio | scheduler/publication_context.py: mark_external_delivery; database/publish_jobs.py: mark_external_started; scheduler/bot_post*.py | Revalidar origem/estado/posse e claim na última barreira, antes de upload/POST; chamadas sem contexto exigem tratamento separado |
| Reconciliação/alteração | api/routers/posts.py; database/schedulers.py: cancel_central, expedite_central | Nenhuma reconciliação, exclusão ou antecipação pode apagar origem ou criar autorização |

## Limites intencionais

A identidade composta não congela textos/mídias/snapshots, datas, função ou
modo de dispatch e não certifica rede/OAuth; esses são gates distintos.
Após release/cancel, o link histórico continua existindo, sem autorizar envio.
A proposta **não protege o dispatcher atual** e não impede um owner ou
service_role de criar outro job sem link. Impedir esse desvio exige origem
não removível no produtor e enforcement de todos os escritores/consumidores.
Não usar ausência de link como prova de legado. O manual_retry gera UUID
novo; UNIQUE(publish_job_id) sozinho não resolve a herança de origem.

Locks locais têm ordem definida, mas transações já existentes podem adquirir
locks em outra ordem. Deadlock/timeout deve abortar sem envio; não usar retry
cego. Antes de adoção real, provar concorrência com writers e lifecycle reais,
examinar índices/grants/constraints no schema compartilhado e revisar retenção
LGPD: RESTRICT em links históricos pode impedir cascatas de exclusão.

## Testes e evidência

[Suite PostgreSQL](../tests/sql/test_f4e2b3_postgres.py) executada explicitamente
no job existente de PostgreSQL 16 descartável da CI. Gate de DSN exato:
postgresql://postgres:postgres@127.0.0.1:5432/f4e_test. Um banco novo de nome
gerado f4e2b3_* é criado e removido apenas nesse serviço local.

Pais são montados com migrations reais (001/002/003/012/017/023/035/036,
044/047/053/055/060/061/067/068/069/070/071/072/074); somente os dois ALTERs
profile_id de 038 são extraídos literalmente para posts/schedulers, sem
montar credenciais não utilizadas. Não há fixture artesanal que substitua
os tipos UUID/INTEGER, FKs, defaults ou CHECKs dos pais usados pelo contrato.
Não equivale à réplica integral de todas as migrations/roles/grants do
Supabase, nem prova autorização de produção.

Cobertura: ACL/RLS, link inerte/imutável, vínculos cruzados e rollback,
imutabilidade de pais, lifecycle e legado não vinculado editáveis, unicidade
por ocorrência/rede e por job, bloqueio de mutação concorrente, snapshot
REPEATABLE READ antigo e reaplicação com rollback. Sem envio/cliente externo.

Sintaxe Python verificada sem escrita nem banco no ambiente de trabalho.
**CI/PR/SHA do incremento: registrar na entrega após confirmação; não chamar
estes testes de aprovados antes da execução.** Os contratos estáticos B2
continuam separados dos testes SQL reais.

## Gates e regra comercial vigente

1. Revisão independente da proposta e testes PostgreSQL; DDL real só após
   autorização específica. Não mover o arquivo ao migrador nesta fase.
2. Desenho de origem obrigatória e compatibilidade main+staging, inclusive
   rollback/versões antigas; pedir autorização antes de promover main.
3. Mídia privada realmente retida, OAuth por perfil, quota por rede/dia de
   São Paulo, T−30, service_role, ownership e unknown/reconciliação.
4. Pedido de downgrade/cancelamento **não** reduz direitos nem pausa
   campanhas antes de current_period_end. Só mudança efetiva no fim pago:
   Premium→Pro pausa até seleção de no máximo 2 por perfil; →Free pausa.
   Não implementar billing nem inventar um campo de vigência existente.
5. Só com novas autorizações: reserva executável, campanha e canário em
   conta/rede/destino nomeados. Nunca ativar “para testar” este PR.

Gatilho SMTP revisto no TASK vivo: sem evidência de domínio próprio
registrado **e configurado**. Sem ação em SMTP/autenticação.
Vault não alterado neste incremento; recomendar espelho no TASK/Guia/39.

Referências: [F4E-2B2](F4E-2B2-IDENTIDADE-INERTE-20261103.md),
[Guia](GUIA-MESTRE-IA.md), [TASK](TASK.md),
[política F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md),
[Vault TASK](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/TASK.md).
