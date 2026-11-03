# F4E-1 — aplicação inerte e gates restantes

## Estado em 03/11/2026

A DDL F4E-1 foi aplicada por coordenação de Rafa ao Supabase compartilhado, após CI #755 e revisão independente. O registro Supabase é versão `20261103191911`, nome `074_f4e1_inert_campaign_reservations`; a linha de `public.migrations` é `074_f4e1_inert_campaign_reservations.sql`. O arquivo canônico em `database/migrations/` é cópia exata da proposta aplicada; seu comentário inicial histórico de “proposta/não executar” permanece para preservar o conteúdo, e não descreve o estado atual.

A inspeção reportada imediatamente após aplicação confirmou tabelas de reservas e ocorrências vazias, RLS habilitado, zero policies, anon/authenticated sem acesso, service_role com SELECT e EXECUTE das RPCs e sem DELETE, um trigger de guarda e o draft legado preservado. Não foram criados jobs, posts ou schedulers F4E; não há executor, merge nem deploy de main/produção. O schema compartilhado foi alterado; isso não implica deploy de aplicação.

A CI [#755](https://github.com/raffastudioproducoes-cloud/shopee_bot-main/actions/runs/41701678290) testou o SQL aplicado em PostgreSQL 16 descartável, com migrations 070/071 reais, pais sintéticos, 15 testes e sem dados reais. Não representa todas as particularidades do Supabase. O resultado da CI do SHA posterior à movimentação deve ser conferido separadamente. Rafa validou em mobile tags, mensagens e perfil; escolha de plano permanece futura.

## Histórico duplo e migrador

O migrador de boot varre `database/migrations/*.sql` e consulta `public.migrations` pelo nome do arquivo. No banco compartilhado o marker informado já existe e deve impedir reaplicação no boot. Em outro banco sem marker, o migrador executa o arquivo e o registra uma vez; esse comportamento não prova equivalência de schema existente.

A DDL usa CREATE explícito e falha em reexecução se os objetos já existirem; não reconcilia drift. Se houver objeto pré-existente inesperado, apenas um dos históricos presente, ou nome/conteúdo divergente, parar e investigar: não registrar nem reaplicar para mascarar uma falha. Uma mudança de schema posterior exige nova revisão, autorização e estratégia de migração; não alterar este arquivo aplicado. Os dois históricos não devem ser presumidos atomicamente sincronizados por ferramentas diferentes.

## Limites e riscos abertos

- A reserva é `reserved_no_dispatch` ou `released`; ocorrência é `planned` ou `cancelled`; `dispatch_enabled=false` é imposto por CHECK. Nada nesta etapa cria ou despacha posts, jobs ou schedulers.
- RPC SECURITY INVOKER com service_role exige backend autenticado que valide conta/perfil. RLS não protege contra service_role; os privilégios de DML necessários permitem inserções diretas que podem contornar quota e regras da RPC. Trigger valida ownership e liberação terminal, mas não transforma a credencial em identidade de usuário.
- A chave de idempotência é única por conta, inclusive entre perfis. Mesmo payload retorna o mesmo ID após liberação; não reativa. Outra chave não reserva simultaneamente o mesmo draft/revisão.
- Timestamps UTC explícitos e futuros, janela de plano, contagem de slots e limites são guardas preparatórias; slots não representam redes. Não há validação por rede/OAuth, conflitos de agenda ou autorização de publicação.
- Locks sobre draft/mídias não comprovam retenção física de objetos no Storage nem cobrem necessariamente todos os fluxos externos/concorrentes. Metadados em snapshot não garantem que o arquivo continue disponível.
- F4E-2 (barreiras de dispatcher em ambos ambientes, integração de backend, políticas por rede e executor) depende de avaliação, testes e aprovação separados. Não ativar com base apenas nesta DDL.
- Reavaliar exclusão, downgrade, auditoria de acesso, retenção LGPD, ACLs efetivas e drift no contexto real antes de integrar a aplicação. VERSION continua `3.0.0`.
