# Agendador funcional em staging e main com Supabase compartilhado — 02/11/2026

## Falha relatada

O botão de publicação da staging devolvia HTTP 503 (“Agendador indisponível”). O código do scheduler era o mesmo nas duas branches, mas a variável de serviço `SCHEDULER_ENABLED=false` mantinha a execução desligada em staging para evitar disparos duplicados na tabela PostgreSQL `apscheduler_jobs`, usada simultaneamente por ambas as instâncias. O APScheduler 3.x não suporta múltiplos schedulers consumindo o mesmo jobstore.

Isso contraria a finalidade do ambiente: implementar e testar **todas as funções** em staging antes da promoção a `main`.

## Solução técnica

1. **Mesma versão de código:** o ambiente é derivado do `RENDER_GIT_BRANCH` injetado pelo Render. `main` corresponde a `production`; `staging` corresponde a `staging`. Branch desconhecido falha fechado, evitando que um preview/projeto diferente execute dados reais. Localmente é possível definir `SCHEDULER_ENVIRONMENT`.
2. **Mesma base Supabase:** migration aditiva `067_isolate_scheduler_environments.sql` adiciona `schedulers.environment` com `DEFAULT 'production'`. Todos os jobs existentes continuam da produção, sem alteração dos horários, IDs, clientes ou histórico. Novas agendas criadas no staging recebem `staging`. Novas agendas em main recebem `production`.
3. **Jobstore dedicado por ambiente:** `apscheduler_jobs` continua reservado à main; `apscheduler_jobs_staging` passa a persistir apenas as datas/horas do staging. Não se compartilha APScheduler JobStore entre dois processos. A nova tabela usa RLS, revoga acesso público/anônimo e índice `next_run_time`.
4. **Fila durável protegida:** `recoverable`, `expire_running` e `claim` de `publish_jobs` agora exigem a igualdade `schedule.environment = ambiente_atual`, além de usuário/perfil/post. `schedulers.get_by_id` e a atualização de jobs antigos também respeitam o ambiente. `publication_claims` e `idempotency_key` mantêm proteção por scheduler/ocorrência.
5. **Legado seguro:** `trigger=date` e jobs recorrentes antigos continuam na tabela original e só main os executa. O migration não move nem limpa filas existentes. A função de disparo `Agora` permanece através do scheduler do próprio ambiente.
6. **Uma instância por serviço:** `gunicorn.conf.py` mantém `workers=1`; não aumentar trabalhadores/instâncias sem tornar o APScheduler 3.x seguro também dentro de um mesmo ambiente. Os dois sites compartilham registros de posts/contas/mídias: o **ambiente de execução** é separado, não a visibilidade dos dados.

## Ordem de rollout (obrigatória, não inverter)

- [ ] PR da correção em `staging` e CI de scheduler/API/SQL verdes.
- [ ] Render staging live no novo SHA, com `SCHEDULER_ENABLED=false` **temporariamente**, aplicando a migration aditiva 067. Conferir no Supabase a nova coluna/tabela, a migração registrada e a preservação das agendas de produção.
- [ ] PR `staging` → `main`, CI verde; aguardar Render produção live com filtros de ambiente ativos e validar health, scheduler, credenciais e conta `RafaelTesteCliente` sem alterar login nem dados.
- [ ] **Só depois do passo anterior**, atualizar via Render apenas `SCHEDULER_ENABLED=true` no serviço de staging (merge das variáveis, sem substituir as existentes) e aguardar novo deploy live.
- [ ] Comprovar nos logs a inicialização `Scheduler initializing in staging`, disponibilidade do bridge e funcionamento da agenda de staging. Conferir que filas antigas da produção não passaram para staging.
- [ ] Testar criação de agendamento para cliente de teste com destino de publicação explicitamente autorizado; não criar/publicar posts reais nem mexer nas credenciais durante smoke técnico.

**Por que essa sequência?** A versão de produção anterior varria `publish_jobs` globalmente. Ligar staging antes de promover os filtros poderia fazer a produção antiga consumir testes do novo ambiente; por isso a ativação da variável é a última etapa, após o deploy de proteção em main.

## Contratos e testes

- Branch do Render determina ambiente, ignorando qualquer override conflitante.
- Mesmo dia/hora/produto e múltiplos clientes: agendas têm IDs UUID distintos e idempotência por ocorrência; filtros novos não juntam envs nem usuários.
- Retomada de `pending` e expiração de `running` só no ambiente dono da agenda.
- Jobs `unknown` não são reenviados automaticamente; status de resultado não é reinterpretado.
- Quem cria em staging observa o mesmo formulário, validações, preview e jobs que em main, com o novo owner `staging`.
- CI mockado não comprova entrega nas APIs externas. Conexões Threads, Shopee e demais plataformas mantêm suas regras/OAuth próprios; Render Free pode suspender o processo e atrasar horários. Não há garantia de disparo pontual com web service Free suspenso.

## Fonte e rastreabilidade

- `scheduler/__init__.py`, `database/schedulers.py`, `database/publish_jobs.py`, `database/scheduler_environment.py`, `database/migrations/067_isolate_scheduler_environments.sql` e `gunicorn.conf.py`.
- Documentação do [APScheduler 3.x](https://apscheduler.readthedocs.io/en/3.x/userguide.html) afirma que dois schedulers não devem compartilhar jobstore.
- Variável `RENDER_GIT_BRANCH` documentada em [Render Default Environment Variables](https://render.com/docs/environment-variables).
- Evidências de CI/PR/deploy e SQL de verificação devem ser acrescentadas após cada fase, sem confundir implementação com produção.
