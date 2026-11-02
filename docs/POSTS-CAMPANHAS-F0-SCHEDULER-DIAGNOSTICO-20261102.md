# F0 — Diagnóstico técnico do agendador staging/produção (02/11/2026)

**Estado:** diagnóstico inicial concluído por inspeção do código; correção integral **ainda pendente**. Apenas branch `feat/campanhas-listas-20261102`, sem mutar Supabase nem serviços Render.

## Contrato de produto confirmado

- Staging é usado somente pelo Rafa, dono/desenvolvedor, para preparar e testar antes de aprovar mudanças; clientes finais acessam a produção.
- Os dois sites compartilham Supabase; um post agendado no staging deve ser consultável pela produção e enviado **uma única vez** pelo executor responsável.
- O Supabase cron já acorda a produção; não há necessidade de outro cron que execute postagens em staging. Mesmo sem clientes em staging, dois workers em segundo plano **podem** consumir um evento se apontarem para o mesmo escopo; é a identidade/claim que evita duplicidade.
- `main` só recebe mudanças de staging aprovadas por Rafa.

## Causa raiz verificada no código atual

1. `database/scheduler_environment.py::current_environment()` escolhe `staging` no Render branch `staging` e `production` no branch `main`.
2. `database/schedulers.py::insert()` grava `schedulers.environment=current_environment()`, portanto uma agenda nova criada pelo staging recebe `staging`.
3. `database/schedulers.py::get_by_id()` e `get_publication_jobs()` filtram por `s.environment=current_environment()`. A produção não enxerga a agenda marcada `staging`.
4. `database/publish_jobs.py::{recoverable,expire_running,claim}` também filtram `schedule.environment`, impedindo o worker da produção de recuperar o job de staging.
5. `web/routes/internal.py::create_job()` cria por `shopee_bot.scheduler.add_job()` dentro do processo Flask local; cada ambiente usa jobstore diferente (`apscheduler_jobs` ou `apscheduler_jobs_staging`), conforme `docs/SCHEDULER-ENVIRONMENTS-20261102.md`.
6. `web/routes/cron_wakeup.py` só desperta o scheduler já inicializado do serviço que recebe o HTTP. Acordar a produção não migra nem copia jobs do jobstore exclusivo de staging.

**Conclusão:** o problema não depende de quantos usuários entram no staging. No código atual, uma programação criada nele fica vinculada ao executor de staging. Esse comportamento conflita com a autoridade única de publicação definida pelo Rafa.

## Correção planejada (não aplicada)

- Separar **origem da edição** (`current_environment`) de **autoridade do disparo** (`publication_executor_environment` = produção após validar branch). A primeira etapa dessa interface tem teste RED→GREEN no PR #198; ela ainda não altera o scheduler.
- Persistir intenção de criação, edição e cancelamento em registro durável compartilhado. O executor central deve reconciliar e reivindicar exclusivamente ocorrências destinadas à produção, inclusive aquelas criadas no staging.
- Migrar de modo compatível eventuais agendas `environment=staging` já existentes, após auditoria read-only de IDs/horários e conferência de jobs em execução. Não simplesmente atualizar todas linhas ou deletar jobstore.
- Desligar execução de publicação em staging **somente depois** do novo executor de produção reconhecer as intenções provenientes do staging; manter API/front igualmente funcionais.
- Preservar `Agora` e `Recorrente` e garantir que edição/cancelamento reflitam no processo de execução central. Cenários sem executor disponível devem dar estado claro e nunca simular sucesso.
- Rastrear `publish_jobs` e `publication_claims` para impedir repetição externa se execução terminar em `unknown` ou se duas instâncias disputarem o mesmo slot.

## Testes exigidos antes de qualquer deploy

- Mock de criação em staging e leitura/claim em produção; edição e cancelamento em staging interrompem apenas jobs futuros.
- Dois workers disputam o mesmo job/mesmo minuto e só um inicia API externa.
- Usuários/perfis diferentes, mesmo segundo, produto repetido não vazam dados nem se bloqueiam.
- Agendas antigas em produção mantêm IDs, horários, estado, histórico; nenhuma duplicação após migração.
- Fluxo `Agora` do staging tem resultado claro, sem fila local oculta ou confirmação falsa.
- Supabase cron provoca recuperação/execução na produção no momento correto.
- Sem publicações reais de teste sem destino expressamente autorizado.

## Evidência automatizada inicial

- Teste criado em `tests/scheduler/test_central_dispatch_contract.py` na branch de trabalho.
- Primeira CI, SHA `9e0b430`, [run 41504113317](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41504113317): falha RED esperada `ImportError: cannot import name 'publication_executor_environment'`. Isso prova que a interface de autoridade central ainda faltava no código; **não** prova que o pipeline inteiro foi corrigido.
- SHA `a2c8e4e` adicionou a função de contrato, sem alterar worker ou dados. A verificação GREEN e os testes mais amplos ficam registrados após a CI correspondente.

## Próxima implementação

Completar Task 1/2 do [plano de execução](superpowers/plans/2026-11-02-campanhas-listas-implementacao.md): testes de criação→reconciliação→claim, desenho de persistência do comando de agenda e rollout compatível. Não declarar F0 como concluída antes do cenário staging→produção se tornar comprovadamente funcional.

## F0 — checkpoint adicional: regressões automatizadas (02/11/2026)

- Commit [`1b5cb3b`](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/commit/1b5cb3b13d77682b19e71f88740b292c94aee30d) acrescentou `tests/scheduler/test_central_dispatch_gap.py`, exclusivamente com simulações; não mexeu no runtime nem no banco.
- Três testes demonstram os filtros atuais por ambiente e o registro no scheduler local. Um quarto contrato de execução centralizada permanece `xfail(strict=True)`: é uma lacuna **esperada**, não uma correção já entregue.
- [CI #41527390056](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41527390056) concluído com verificações Python e frontend aprovadas; os jobs externos e a prévia Supabase foram pulados.
- Próximo gate: auditoria **somente leitura, com autorização aplicável**, das agendas de staging e jobs antigos antes de propor compatibilidade/migração; depois teste da solução com o fluxo `Agora`, recorrência, cancelamento, claims concorrentes e estados `unknown`. Nenhum teste E2E externo foi realizado.

## F0 — auditoria read-only do Supabase compartilhado (02/11/2026, 18h32 Brasília)

**Autorização:** leitura expressa do Rafa; somente `SELECT` de metadados estruturais e agregados. **Nenhuma** alteração de linha, execução de migration, mudança de ambiente, leitura de conteúdo de post/credenciais/job_state ou chamada a rede social. Snapshot observado em `2026-11-02 21:32:18+00`; contagens podem mudar com a atividade normal do serviço.

### Inventário real

| Recurso | Produção | Staging | Interpretação |
|---|---:|---:|---|
| `schedulers` | 6 (2 cron, 4 date) | 5 (5 cron) | `environment` identifica a origem atual, não autoridade central |
| Jobstore APScheduler persistido | 3 | 6 | Em cada tabela: 1 job interno `publish_queue_recovery`; 2 cron de produção e 5 cron de staging |
| Agendas com ID no próprio jobstore | 2 | 5 | Nenhum ID de scheduler aparece em **ambos** os jobstores |
| Agendas `date` sem jobstore | 4 | 0 | As 4 têm data passada e histórico em `publish_jobs`; isso **não** prova perda de agenda futura |
| `publish_jobs` `succeeded` | 4 | 0 | Somente Threads nas linhas observadas |
| `publish_jobs` `unknown` | 6 | 2 | **Estado terminal/incerto; não autoriza retry** |

- Dos **8** registros `unknown`, **6** têm `external_started_at` preenchido (4 produção, 2 staging). Os outros 2 não têm essa marca, mas também não podem ser reenviados cegamente sem conciliação.
- Os **5** agendamentos recorrentes do staging apontam para **um único post, usuário e perfil**; já iniciaram a janela de vigência. Isso aumenta o risco de transferência automática de um conjunto de testes para a autoridade de produção.
- No instante da consulta, os próximos disparos registrados (sem contar recuperação) iam de **03/11 15h a 18h** no jobstore de produção e de **02/11 21h a 03/11 18h** no de staging (horários Brasília). Nenhuma entrada listada estava atrasada nessa amostra.
- `publication_claims` tinha **1** linha, criada em 30/10. Auditar comportamento de TTL/renovação no código; **não** remover nem inferir que o claim ainda bloqueia.
- As tabelas envolvidas têm RLS habilitado (segundo inventário). O diagnóstico não valida as políticas para futuras tabelas de campanha.

### Implicações técnicas e bloqueio de rollout

1. **Não reidratar as 4 agendas `date` da produção** por ausência no jobstore: são antigas, possuem histórico e podem ter sido consumidas normalmente. A correlação de históricos por status/identidade deve reger qualquer recuperação.
2. **Não converter automaticamente as 5 agendas atuais do staging** nem apagar o jobstore staging antes de decidir com Rafa se são testes descartáveis ou agendas que devem permanecer e passar à produção. O staging ainda possui executor próprio hoje.
3. **Não repetir os 8 `unknown`** (inclusive os 6 marcados como operação externa iniciada). Guardar identidade, status e trilha; conciliação externa deve ser explicitamente autorizada e preferencialmente de leitura.
4. A correção da Task 2 precisa de transição **feature-gated**, preservando IDs, escopo `user_id/profile_id/post_id`, chave de ocorrência e histórico, sem dois workers responsáveis por novas chamadas externas. Primeiro compatibilidade em código e testes; depois migração/configuração sob autorização própria, com ordem de deploy e rollback seguros.
5. A origem da agenda (`staging`/`production`) deve continuar rastreável; a autoridade para publicar é **produção**. Edição/cancelamento precisam chegar ao executor central de modo durável e idempotente, inclusive para o fluxo `Agora`.

**Gate de decisão com o Rafa:** o que fazer com os cinco cron ativos de staging: (A) preservá-los para transferência futura à produção, após homologação controlada; ou (B) tratá-los como testes e pausá-los/encerrá-los antes da transição? Nenhuma das alternativas foi executada. Até a resposta: somente testes e implementação isolada na branch DRAFT, sem ativação/migração.

## F0 — núcleo de execução central com gate desligado (02/11/2026)

**Estado do código no PR #198:** fluxo de reconciliação implementado na branch DRAFT, **não implantado, não migrado, não ligado**. A opção 3 do Rafa está vigente: preservar integralmente os cinco cron legacy ativos de staging; resolver seu destino separadamente após homologação.

- `database/migrations/068_central_dispatch_compatibility.sql` acrescenta `dispatch_mode` (default `legacy`), `dispatch_revision` e `dispatch_cancelled_at`. Não atualiza dados existentes, não apaga tabelas e não toca `apscheduler_jobs*` ou a fila. **Arquivo SQL ainda NÃO executado.** Como `database.init()` chama `run_migrations()` no boot, fazer deploy dessa branch pode aplicar o DDL aditivo ao banco compartilhado: isso requer autorização separada.
- `database/central_dispatch.py` define `ORBITAL_CENTRAL_DISPATCH_ENABLED`, **`false` por padrão**. Valor inválido falha fechado. `legacy` continua por ambiente; somente `central` opt-in e não cancelada fica elegível ao executor de produção.
- `database/schedulers.py` mantém o formato/ordem de INSERT original com gate `false`, usa `dispatch_mode=central` apenas quando autorizado e cria métodos de intenção durável de `Agora`, listagem para reconciliação e cancelamento lógico. Histórico central não é apagado no `DELETE` físico, reservado ao modo legado.
- `database/publish_jobs.py` limita recuperação, expiração de lease e claim aos registros `legacy` do ambiente quando gate desligado; quando ligado, produção também enxerga `central` de ambos os ambientes, enquanto staging vê somente seu legado. `unknown` continua terminal e não se repete.
- `scheduler/central_reconciler.py` registra apenas espelhos `central:<uuid>` no jobstore persistido da produção, reconciliando criação/revisão/cancelamento a cada 30 segundos e no startup; deixa IDs legados intocados. A função de publicação central recusa rodar se gate desligado, se não estiver em produção ou se a agenda central não estiver ativa. Staging não adiciona novos jobs centrais ao jobstore local.
- Testes mockados `test_central_dispatch_mode.py`, `test_central_dispatch_query_scope.py` e `test_central_reconciler.py` somam proteção de ambiente, posse, `Agora`, histórico, revision, espelho e gate/rollback. A CI [#41533585972](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41533585972) passou (API/testes e frontend); staging externo foi pulado. O run anterior [#41533071158](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41533071158) revelou três expectativas de parâmetros legados, corrigidas mantendo o INSERT original com gate desligado.

### Gate de segurança antes da homologação

1. **Não ativar `ORBITAL_CENTRAL_DISPATCH_ENABLED` agora.** Gate não foi habilitado no Render; nenhuma API de provedor foi chamada pelos testes.
2. Validar em ambiente seguro o ciclo staging → registro central → reconciliador em produção → claim único → status, incluindo duas instâncias disputando o mesmo slot e o caso `Agora` quando serviço de produção estiver indisponível. Na integração final, a UI deve declarar claramente `pendente`/`indisponível` em vez de sinalizar uma publicação confirmada antes da execução.
3. Verificar especialmente `date` perdido há mais de uma hora, retries do comando `Agora` e edit/cancel durante execução; hoje o reconciliador exclui horários `date` mais antigos que o grace de 1 hora sem produzir por si só um estado de expiração visível. **Bloqueio de ativação** até resolução desse gap e teste E2E.
4. Planejar rollout com compatibilidade: primeiro migration aditiva + ambos os serviços com código novo e flag `false` (após aprovações); ligar o reconciliador **só na produção**; confirmar sua saúde; só então ligar intenção central para agendas novas do staging. Os cinco legacy staging não entram na reconciliação e continuam sob o executor antigo até decisão explícita. Não criar outro Supabase cron.
5. Rollback: com flag `false`, mirrors centrais não podem chamar provedores e `publish_jobs` exclui central da recuperação; as intenções centrais ficam **suspensas** e precisam de reconciliação/reativação deliberada, sem replay cego. Não voltar a código antigo ou apagar migração sem análise de dados novos.

**F0 ainda NÃO está concluída:** testes unitários e CI não substituem verificação real de duas instâncias, estado de expiração, contrato de disponibilidade e gate de deploy autorizado.
