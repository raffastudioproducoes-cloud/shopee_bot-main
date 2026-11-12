# Migração dos agendamentos da staging para a produção — 12/11/2026 (UTC)

**Ordem de Rafa:** passar todos os agendamentos criados no site de teste para o ambiente de produção, sem recriar,
para o cron de despertar (que só acorda a produção) e o executor da produção os reconhecerem.

## O que foi alterado (banco compartilhado, uma transação com conferência de contagem)
| Tabela | Campo | De → Para | Linhas |
|---|---|---|---|
| `campaign_reservations_f4e` | `source_environment` | `staging` → `production` | 1 (reserva `802f4c82-c8de-417c-9473-022f3ad859b8`) |
| `campaign_network_slots_f4e` | `source_environment` | `staging` → `production` | 450 (420 planejados) |
| `schedulers` | `environment` | `staging` → `production` | 450 (slots da campanha) + 1 recorrência diária (`9528490e-85cf-430a-b333-90cc268575de`, 09:00 BRT) |
| `apscheduler_jobs_staging` → `apscheduler_jobs` | linha do job da recorrência | movida | 1 |

Não alterados: campanhas canceladas (450 slots), histórico já concluído de outras tabelas, credenciais e tabelas `platform_*`/`billing_*`.

## Por que é necessário
A execução é isolada por ambiente (`SCHEDULER_ENVIRONMENT`): a produção só executa o que tem ambiente `production`, e usa a tabela
de jobs `apscheduler_jobs` (a staging usa `apscheduler_jobs_staging`). Campanhas rodam pela fila do banco (`claim_campaign_publication_f4e`),
filtrando por `source_environment`.

## Cópia de segurança e reversão
Valores antigos em `public.migration_backup_staging_to_production_20261112` (903 linhas). Para reverter:
```sql
UPDATE public.campaign_reservations_f4e r SET source_environment = b.valor_antigo
  FROM public.migration_backup_staging_to_production_20261112 b WHERE b.tabela='campaign_reservations_f4e' AND r.id::text=b.chave;
UPDATE public.campaign_network_slots_f4e s SET source_environment = b.valor_antigo
  FROM public.migration_backup_staging_to_production_20261112 b WHERE b.tabela='campaign_network_slots_f4e' AND s.id::text=b.chave;
UPDATE public.schedulers s SET environment = b.valor_antigo
  FROM public.migration_backup_staging_to_production_20261112 b WHERE b.tabela='schedulers' AND s.id::text=b.chave;
INSERT INTO public.apscheduler_jobs_staging (id, next_run_time, job_state)
  SELECT id, next_run_time, job_state FROM public.apscheduler_jobs WHERE id='9528490e-85cf-430a-b333-90cc268575de' ON CONFLICT (id) DO NOTHING;
DELETE FROM public.apscheduler_jobs WHERE id='9528490e-85cf-430a-b333-90cc268575de';
```

## Estado após a migração
Próxima execução na produção: recorrência 12/11 12:00 UTC; campanha 12/11 13:00 UTC (420 slots até 10/12). O cron de despertar chama a produção 3 a 4 minutos antes.

## Não validado
A produção ainda não executou nenhum desses agendamentos. Dependências que não consegui verificar daqui: credenciais de rede (Threads) legíveis pela produção (mesma chave de criptografia) e flags do serviço de produção.
