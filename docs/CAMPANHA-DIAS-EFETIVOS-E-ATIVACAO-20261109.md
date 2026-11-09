# Campanhas — dias efetivos do plano e ativação sem rascunho manual

**Data:** 09/11/2026  
**Versão-base:** 3.8.0  
**Versão candidata:** 3.8.1 (PATCH, staging)  
**Branch:** `fix/campaign-weekday-quota-optional-activation-20261109`  
**Destino planejado:** staging  
**Status:** correções de revisão incorporadas na branch; CI de regressão pendente; PR #386 sincronizada em staging; migration 095 ainda não aplicada.

## 1. Regra de negócio

O limite `campaign_days` representa dias efetivos de publicação, não a quantidade de datas corridas entre início e fim.

- Segunda=0, terça=1, quarta=2, quinta=3, sexta=4, sábado=5, domingo=6.
- A contagem inclui início e fim quando o weekday da data estiver selecionado.
- Dias desmarcados não consomem a cota.
- O limite comercial continua sendo o valor de `campaign_days` do plano, limitado a 30 dias efetivos.
- A janela física máxima é 210 dias corridos inclusivos, suficiente para consumir 30 ocorrências de um único weekday.
- O planejador continua limitado a 450 horários (30 dias efetivos × 15 postagens/dia).

### Exemplo

01/11/2026 a 30/11/2026 com segunda, quarta, sexta e domingo:

| Indicador | Valor |
|---|---:|
| Dias corridos | 30 |
| Dias selecionados dentro do período | 18 |
| Limite Premium | 30 |
| Saldo de dias efetivos | 12 |
| 30ª ocorrência selecionada desde 01/11 | 21/12/2026 |

A interface deve exibir o saldo e a data-limite, incluindo o último horário da distribuição diária. Com uma postagem por dia, usa-se o horário inicial; com mais de uma, usa-se o horário final.

## 2. Limite do período e período pago

Frontend e backend calculam o mesmo conceito de dia efetivo. A data máxima do datepicker é a ocorrência do N-ésimo weekday selecionado, onde N é o limite de dias do plano.

Se houver `campaign_paid_through`, a data máxima efetiva também é limitada pelo último horário que ainda antecede o término do período pago. O comparativo usa o fuso `America/Sao_Paulo`; o slot final precisa ser estritamente anterior ao timestamp de expiração.

A função frontend `frontend/src/lib/campaignSchedule.ts`:
- interpreta datas civis sem deslocamento de fuso;
- conta weekdays selecionados no intervalo;
- calcula saldo e N-ésima ocorrência;
- calcula o último horário diário;
- aplica o limite adicional do período pago;
- formata a data para pt-BR.

## 3. Camadas de validação

### Frontend

`CampaignPlanner.tsx` deixa de comparar apenas dias corridos. A prévia verifica:
- intervalo entre 1 e 210 dias corridos;
- ao menos um weekday selecionado dentro do intervalo;
- quantidade de dias efetivos não superior à cota;
- data final dentro da data máxima calculada;
- horários e postagens/dia dentro dos limites.

O seletor de weekdays usa `--mint-400` e `--text-on-mint` para um estado selecionado claramente visível.

Ações desabilitadas exibem o motivo conhecido: consulta do plano, plano sem campanhas, campos ausentes, lista/produtos inválidos, frequência fora da cota, período pago ou limite de campanhas ativas. Uma falha de consulta não libera operação por inferência.

### API

`api/campaign_schedule.py` define o teto físico de 210 dias e disponibiliza `count_campaign_days`.

`api/campaign_policy.py` valida:
1. janela física de até 210 dias;
2. pelo menos um dia selecionado no período;
3. limite absoluto de 30 dias efetivos;
4. limite comercial `policy.campaign_days`;
5. limite de postagens por dia.

A resposta de limites também considera a cota de campanhas ativas: se a conta já atingiu `active_campaigns_limit`, `activation_available` retorna falso e a mensagem explica o motivo. Falha de leitura da contagem continua bloqueando a ativação.

### RPC SQL / Supabase

`database/migrations/095_campaign_active_weekday_quota.sql` substitui `public.reserve_campaign_f4e` de forma compatível. A função:
- mantém ownership, papel, tier, lock da conta, revisão do rascunho e idempotência;
- mantém limite de 450 ocorrências, validação UTC, datas futuras, slots por dia e mídia pronta;
- valida weekdays 0–6;
- conta datas do intervalo que correspondem aos weekdays;
- rejeita mais de 210 dias corridos ou mais dias efetivos que o limite do plano;
- rejeita ocorrência em weekday não selecionado.

A migration não cria nem remove tabelas e não altera dados. Ela altera uma função usada na reserva atômica.

## 4. Rascunho manual opcional

O motor F4E exige um snapshot persistido para revisão, ownership, mídia e idempotência. Esse requisito interno é mantido.

Comportamento da interface:
1. Se existir rascunho manual atualizado, a ativação usa seu ID/revisão.
2. Se não existir rascunho ou houver alterações, “Ativar campanha” cria/atualiza o snapshot internamente e chama a ativação em sequência.
3. A pessoa não precisa clicar em “Salvar rascunho”.
4. Se a ativação falhar, o snapshot fica recuperável para uma nova tentativa.
5. Campanhas confirmadas como ativas/pausadas/canceladas/concluídas deixam de aparecer na lista de rascunhos; registros em `preparing` permanecem recuperáveis.
6. O fluxo reutiliza o mesmo ID/revisão e a idempotência existente. Não deve criar uma segunda reserva ao repetir uma tentativa.

O botão manual “Salvar rascunho” continua independente e opcional.

## 5. Arquivos alterados nesta implementação

- `frontend/src/lib/campaignSchedule.ts` — cálculo puro de dias efetivos e data/hora-limite.
- `frontend/src/components/campaigns/CampaignPlanner.tsx` — validação, aviso, razões de bloqueio e ativação sem salvamento manual.
- `frontend/src/components/campaigns/campaignPlanner.css` — contraste do weekday selecionado.
- `frontend/src/api/planUsage.ts` — contrato tipado do estado de cota e mensagem de ativação.
- `api/campaign_schedule.py` — teto físico de 210 dias e contador de dias efetivos.
- `api/campaign_policy.py` — validação comercial por weekday e bloqueio de novas campanhas quando a cota ativa está cheia; retry da mesma preparação é permitido somente após confirmação do lifecycle, da consulta de uso e do período pago.
- `api/routers/campaigns.py` — paginação por lotes, filtro de lifecycle antes do limite de 30 e resposta HTTP 503 se a consulta de reservas falhar (fail closed).
- `database/migrations/095_campaign_active_weekday_quota.sql` — atualização da guarda atômica da reserva.
- `tests/api/test_campaign_schedule.py` e `tests/api/test_campaign_policy.py` — regressões de calendário, plano, SQL, cota ativa, paginação e fail-closed.
- `tests/api/conftest.py` — paginação realista por `.range()` no FakeDB.
- `tests/sql/test_f4e2b5_postgres.py` — valida que service_role não executa a RPC legada e executa o wrapper autorizado.
- `frontend/tests/plan-access.test.mjs` — protege o retry da mesma preparação e a preservação de edições durante ativação.
- `frontend/tests/campaign-schedule.test.mjs` — exemplo 18/30, data 21/12 e contrato de ativação opcional.

## 6. Validação necessária

Testes direcionados:
1. Exemplo de novembro: 18 dias usados, 12 restantes e limite em 21/12/2026.
2. Pro: 15 terças selecionadas aceitas em intervalo maior que 30 dias corridos; 16 rejeitadas.
3. Premium: 30 dias selecionados em intervalo estendido aceitos; 211 dias corridos rejeitados.
4. Nenhum weekday no intervalo e weekday fora de 0–6 rejeitados.
5. Cota de campanhas ativas cheia bloqueia ativação; abaixo da cota permite.
6. Frontend: weekday ativo em alto contraste e ativação sem clique manual de salvar.
7. TypeScript/Vite, testes frontend e CI obrigatória da PR.
8. Listagem com mais de 30 snapshots, com os primeiros 30 já ativados, deve devolver os snapshots recuperáveis mais antigos.
9. Falha na leitura de lifecycle deve responder 503 sem expor snapshot como editável.
10. Ativação concorrente com edição do formulário não pode apagar as alterações novas.
11. Retentativa de `preparing` deve ser permitida na cota cheia apenas para o mesmo draft; campanha nova continua bloqueada.
12. ACL PostgreSQL: `service_role` sem EXECUTE na RPC v1 e com EXECUTE no wrapper v2.

Não executar publicação real, agendamento externo, upload ou ação na Shopee durante testes.

## 7. Portão de aprovação para staging

A migration 095 será aplicada automaticamente pelo migrador no boot da aplicação quando chegar ao staging. O Supabase é compartilhado com produção; portanto, o merge em staging altera a função SQL compartilhada.

**A migration está apenas no branch e não foi aplicada.** Rafa autorizou expressamente sua aplicação por meio do deploy de staging, mas o portão técnico permanece: só integrar e implantar depois de CI verde, revisão final e reconciliação da branch com a staging atualizada. O Supabase compartilhado significa que a DDL ficará visível à produção assim que o boot do staging aplicar a migration. A função mantém a assinatura anterior e preserva a ACL da migration 076, reforçada por REVOKE explícito na migration 095.

Depois da autorização:
- CI verde e revisão do diff SQL;
- merge somente para staging;
- conferir migration 095 aplicada;
- confirmar Render staging LIVE no SHA correto;
- smoke básico e homologação de Rafa;
- produção somente após autorização separada.

## 8. Revisão de segurança e robustez — 09/11/2026

A revisão automatizada identificou cinco pontos. Foram incorporadas correções para:

- ACL da RPC legada: a migration 095 agora executa REVOKE explícito de EXECUTE para PUBLIC, anon, authenticated e service_role na função v1; concede EXECUTE apenas ao wrapper reserve_campaign_networks_f4e para service_role. O teste PostgreSQL verifica os dois lados da permissão.
- Listagem de rascunhos: consulta paginada em blocos de 100; remove lifecycle active/paused/cancelled/completed antes de limitar a 30 itens recuperáveis.
- Falha de leitura de reservas: responde HTTP 503 e não apresenta estado incerto como rascunho editável.
- Preservação de edição: o formulário só é limpo se a assinatura atual ainda corresponder ao snapshot efetivamente ativado.
- Retentativa: quando o mesmo draft possui reserva preparing, a UI permite retry na cota cheia somente se a leitura de uso está disponível e o período pago permanece confirmado. Novas campanhas seguem bloqueadas.

**Validação dessas correções ainda pendente.** Não declarar os findings encerrados até CI, SQL descartável e nova revisão confirmarem o comportamento. Migration 095 não aplicada; staging e produção ainda não receberam esta implementação.
