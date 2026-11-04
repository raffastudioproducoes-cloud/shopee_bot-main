# F4E-2B2 — identidade persistente inerte e decisão de downgrade (03/11/2026)

**Estado:** contrato preparatório integrado somente no `staging` (PR #234, SHA `0483b7a`; correção CI PR #235, SHA `1363024`), Render `dep-dbl4e317lnhs739rukhg` LIVE, CI e smoke de staging aprovados. A proposta SQL continua NÃO APLICADA ao Supabase. Não existe ativação, reserva executável, job de campanha ou autorização para publicação; `main` preservada.

## Decisão de produto — retificada em 03/11/2026

**Regra vigente:** pedido de downgrade Premium→Pro ou cancelamento para Free **não pausa** campanhas nem reduz direitos no momento do pedido. O ciclo quitado permanece íntegro. Somente **no fim da vigência paga** e após a transição efetiva o guard deve pausar as campanhas com segurança: Premium→Pro pausa todas, permitindo escolha explícita de até 2 por perfil após revalidação; →Free pausa todas. Histórico e configuração preservados. Nem pagamento nem executor de campanha existem atualmente; regra futura do checkout e da execução.

A decisão anterior de “pausar imediatamente ao passar de Premium para Pro” agora se refere **exclusivamente ao instante da mudança efetiva do plano, nunca ao pedido agendado**. Caso o cliente exerça arrependimento legal ou haja rescisão/reembolso exigível, não presumir permanência obrigatória até vencimento. Consultar [política de assinaturas, seção 12](PLANOS-F4-POLITICAS-E-FASES-20261103.md#12-transições-de-assinatura-e-comunicação--decisão-corrigida-de-rafa-03112026).

## O que esta preparação faz

1. Corrige a estrutura `CampaignDispatchIdentity`: `schedulers.id` e `publish_jobs.id` são UUID; `posts.id` é INTEGER. Inclui `network` e exclui as redes atualmente desabilitadas.
2. Mantém `require_campaign_dispatch_authorization` **sempre recusando** em staging e produção, inclusive com a flag central verdadeira. O DTO é imutável apenas em memória; não certifica nada no banco.
3. Oferece `docs/sql-proposals/F4E2B2-INERT-CAMPAIGN-DISPATCH-LINKS.sql` **fora de `database/migrations`**. A proposta cria uma tabela exclusivamente de leitura ao `service_role`, com campos obrigatórios, FKs, unicidade por ocorrência+rede, validação cruzada entre reserva/ocorrência/agenda/post/job e bloqueio de alteração ou ativação. Não há INSERT concedido nem mecanismo de dispatch.
4. Testes automatizados validam formato real dos IDs, fail-closed em duas origens/flags e restrições estáticas do SQL. Não substituem execução isolada em PostgreSQL ou teste transacional de concorrência.

## Adendo F4E-2B3 — proposta em revisão, não aplicada

A [F4E-2B3](F4E-2B3-PROPOSTA-IDENTIDADE-PAIS-20261103.md) aprimora este mesmo arquivo SQL com chaves/FKs compostas RESTRICT dos pais, locks ordenados e validação de rede do post. Testes PostgreSQL descartável foram preparados e adicionados explicitamente à CI; resultado/PR ainda pendentes neste registro. A proposta não é idempotente para reaplicação e permanece sem INSERT/UPDATE/DELETE ao service_role. Lifecycle não é identidade: status/cancelamento/claims não são congelados. Não há integração no executor, DDL no Supabase nem proteção operacional. O DTO permanece sem autoridade.

## Lacunas antes de qualquer uso real da identidade

- **Banco:** a proposta não foi executada; exige revisão de locking, validação de FKs/status, concorrência, imutabilidade dos **pais** (reserva/ocorrência/scheduler/post/job), regras para múltiplas redes, retries e histórico sem cascatas destrutivas. Uma FK sozinha não prova identidade estável depois de UPDATE nos pais.
- **Executor:** adicionar identificador durável de origem de campanha, de forma que ausência ou falsificação nunca seja interpretada como post legado; proteger criação, claim, recuperação, retry, reconciliação central e a última barreira **antes do primeiro upload/POST externo**. A consulta/decisão deve ocorrer na mesma transação/claim; flags não podem converter `inert` em autorização.
- **Ambientes:** instalar guardas compatíveis em `main` e `staging` antes de permitir **qualquer** intenção executável no Supabase compartilhado; homologar ambos mesmo sob rollout de versões diferentes. `ORBITAL_CENTRAL_DISPATCH_ENABLED` não é a autorização de campanha.
- **Pré-condições comerciais/segurança:** cota transacional de cada rede em cada dia de São Paulo, reserva por perfil, mídia realmente preservada no Storage privado, autorização OAuth e regras da rede, T−30, ownership `service_role`, pausa por downgrade sem perda de histórico e `unknown` sem reenvio cego.
- **Auditoria:** migração com testes PostgreSQL 16, grants/RLS verificados, nenhum job disparado por seed de testes e logs sanitizados.

## Sequência de rollout futura

1. Concluir desenho e testes PostgreSQL **em banco descartável**, revisar riscos e registrar decisão de SQL.
2. Solicitar **autorização própria** de Rafa para alterar o Supabase compartilhado, se for necessária DDL. Nenhum arquivo desta proposta está no migrador de boot.
3. Preparar guardas de executor compatíveis e pedir **autorização específica** antes de promover a `main`; implantar de modo que jobs legados mantenham semântica e campanhas continuem bloqueadas.
4. Só então, com novas autorizações distintas, permitir reservas executáveis e um teste canário em conta/rede/destino nomeados por Rafa.

## Evidências e escopo negativo

- Base de trabalho: `staging` no SHA `5e9b34c73c8bd1aac1c9e44a2252de6dc18a2999` (PR #233 F4E-2B1 já integrada).
- Versão oficial `VERSION=3.0.0`, sem lançamento.
- **Sem** migração nova aplicada, post publicado, alteração de flag, OAuth, preço, checkout, mudança na `main`, limpeza ou alteração de dados de clientes.
- **Evidências pós-deploy:** CI PR #41713751800 e #41714645658 SUCCESS; esta última executou 15 testes F4E-1 em PostgreSQL descartável e 3 contratos estáticos F4E-2B2. CI staging #41714932997, smoke HTTP #41714932664 e ZAP passivo #41714932408 SUCCESS; smoke autenticado SKIPPED sem credenciais. Render LIVE no SHA `1363024`. O bloqueio F4E permanece isolado, não operacional no dispatcher existente; não há tabela proposta no Supabase (read-only, reservas/ocorrências 0/0).

Referências: [Guia Mestre](GUIA-MESTRE-IA.md), [política F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md), [TASK](TASK.md), [AGENTS](../AGENTS.md) e [Vault TASK](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/TASK.md).
