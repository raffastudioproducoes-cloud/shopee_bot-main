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
