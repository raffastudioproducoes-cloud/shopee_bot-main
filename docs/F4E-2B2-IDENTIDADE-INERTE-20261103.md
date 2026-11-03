# F4E-2B2 — identidade persistente inerte e decisão de downgrade (03/11/2026)

**Estado:** preparação de contrato em branch de trabalho. Não existe ativação, reserva executável, job de campanha ou autorização para publicação. Staging e produção compartilham o Supabase; a produção continua na branch `main`.

## Decisão de produto aprovada por Rafa

Quando uma conta cai de Premium (até cinco campanhas ativas por perfil) para Pro (até duas), **pausar todas as campanhas ativas do perfil afetado imediatamente** e impedir disparos até que o titular escolha explicitamente **no máximo duas** para continuar. As demais ficam pausadas e preservam configuração, anexos referenciados e histórico, sem remoção. Não escolher duas arbitrariamente por data, prioridade ou desempenho.

- Cada perfil é isolado. Uma escolha não concede privilégios sobre campanhas de outro perfil.
- A escolha deve ser transacional com revalidação do plano vigente, `users.access`, ownership, cota vigente, mídia física, OAuth, rede, janela e conflitos.
- Enquanto a escolha estiver pendente, **zero publicações de campanha**. Downgrade a Free pausa todas; upgrade futuro não reativa nada automaticamente.
- Um envio já iniciado na rede é potencialmente `unknown`: não se promete cancelamento retroativo nem retry cego. Antes do primeiro envio externo o controle precisa ser atômico.
- A decisão é **política aprovada**, não mecanismo operacional hoje: não há campanhas ativas implementadas.

## O que esta preparação faz

1. Corrige a estrutura `CampaignDispatchIdentity`: `schedulers.id` e `publish_jobs.id` são UUID; `posts.id` é INTEGER. Inclui `network` e exclui as redes atualmente desabilitadas.
2. Mantém `require_campaign_dispatch_authorization` **sempre recusando** em staging e produção, inclusive com a flag central verdadeira. O DTO é imutável apenas em memória; não certifica nada no banco.
3. Oferece `docs/sql-proposals/F4E2B2-INERT-CAMPAIGN-DISPATCH-LINKS.sql` **fora de `database/migrations`**. A proposta cria uma tabela exclusivamente de leitura ao `service_role`, com campos obrigatórios, FKs, unicidade por ocorrência+rede, validação cruzada entre reserva/ocorrência/agenda/post/job e bloqueio de alteração ou ativação. Não há INSERT concedido nem mecanismo de dispatch.
4. Testes automatizados validam formato real dos IDs, fail-closed em duas origens/flags e restrições estáticas do SQL. Não substituem execução isolada em PostgreSQL ou teste transacional de concorrência.

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
- CI, PR, merge e deploy da F4E-2B2 só poderão constar como confirmados **após** verificação posterior. Distinguir esta preparação de controle operacional.

Referências: [Guia Mestre](GUIA-MESTRE-IA.md), [política F4](PLANOS-F4-POLITICAS-E-FASES-20261103.md), [TASK](TASK.md), [AGENTS](../AGENTS.md) e [Vault TASK](https://github.com/raffastudioproducoes-cloud/RaffaStudio-Vault/blob/main/Projetos/ShopeeAutoVendas/TASK.md).
