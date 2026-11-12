# Reset do histórico de posts — 12/11/2026 (UTC)

**Ordem de Rafa:** apagar tudo que já foi postado (com sucesso ou erro) e o que foi cancelado; manter só o que ainda está programado.

## O que foi apagado (conta `rafastudio`, a única com posts; uma transação com conferência de contagem)
- **481 posts**: 450 de campanhas canceladas, 16 publicados, 14 com erro e 1 publicação de campanha sem vaga.
- Em cascata: 481 jobs de publicação, agendamentos, 527 vínculos de mídia, vínculos de produto e 1 registro de métricas (`publication_insights`).
- 480 vagas de campanha (`campaign_network_slots_f4e`) e 3 registros de campanhas antigas (`campaign_reservations_f4e`: 2 canceladas e 1 concluída).

## O que ficou
421 posts: 420 vagas planejadas (campanha ativa `802f4c82-c8de-417c-9473-022f3ad859b8`, 12/11 13:00 UTC até 10/12) e a recorrência diária das 09:00 BRT.
Não foram tocados: mídias da biblioteca (`medias`/Storage), produtos, listas, perfis, credenciais.
Os posts já publicados continuam nas redes (Threads); só o registro no Auto Orbital foi apagado.

## Cópia de segurança
Tabelas `public.bkp_reset_20261112_*` (posts, publish_jobs, schedulers, slots, posts_medias, posts_products, insights, reservations) e a lista de ids
`public.reset_historico_20261112_ids`. Para restaurar (ordem): reservations → posts → schedulers → publish_jobs → slots → posts_medias → posts_products → insights,
cada uma com `INSERT INTO public.<tabela> SELECT * FROM public.bkp_reset_20261112_<tabela>`. Não restaura métricas das redes, só os registros locais.
