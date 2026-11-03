# F4E-2B4 — contrato de origem durável e ordem de rollout (gate técnico)

Data: 03/11/2026. Referência: `staging` após F4E-2B3, PR #238 / `1f0e063`; `VERSION=3.0.0`.
Estado: **especificação de segurança, não implementação de dispatch nem autorização operacional**.

## Decisão de engenharia

**Não conectar uma guarda seletiva ao executor ainda.** `environment` e
`dispatch_mode` descrevem ambiente/topologia; não comprovam que o job seja
de campanha. A versão `main` que compartilha o Supabase não reconhece a
origem F4E; portanto, qualquer campanha inserida prematuramente em
`schedulers`, no jobstore ou em `publish_jobs` pode ser alcançada por
leitores antigos. A proposta SQL F4E-2B2, embora validada como prova
de identidade em PostgreSQL descartável, não está pronta para aplicação
operacional. **Produtores/flags F4E permanecem OFF; zero jobs novos.**

## Invariantes para a implementação mínima

1. A classificação é **positiva e persistida** em `schedulers` e
   `publish_jobs`: campo canônico proposto `publication_origin` com valores
   `legacy` e `campaign`, `NOT NULL`, imutável após criação. No rollout
   aditivo, registros existentes e escritores antigos recebem `legacy`
   explicitamente armazenado por default, não por inferência de link ausente.
   **Origem de campanha exige escrita explícita**, nunca um fallback por erro,
   ausência de link, ID, flag, ambiente ou modo. Os nomes/DDL definitivos
   dependem de revisão de migrations atuais.
2. A identidade de campanha (conta, perfil, reserva, ocorrência, agenda,
   post, rede, job e ambiente) é criada/vinculada **em uma transação**,
   com constraint que impossibilite commit de agenda/job de origem
   `campaign` sem pais íntegros e vínculo correspondente. O vínculo
   é imutável; revalidação de autorização e status é dinâmica. Evitar
   dependência circular sem enforcement no COMMIT e escrever teste de
   rollback para cada ponto de falha. O job deve concordar com a
   origem da agenda; criadores alternativos não podem reclassificar.
3. `legacy` mantém os fluxos atuais e o isolamento entre ambientes.
   Para `campaign`, a recusa é **incondicional** enquanto a fase estiver
   inerte. Leitura indisponível, identidade inconsistente, cancelamento,
   revisão trocada, quota vencida ou lease inválido **recusam envio**;
   `feature_flag=ON` não concede autorização.
4. Os gates incidem em **todos os caminhos**: criação/mirror APScheduler,
   reconciliação, enqueue, claim, recovery, retry, requeue, cancelamento e
   última barreira antes de upload/POST externo. Validar na transação
   e imediatamente antes do efeito externo, com proteção contra corrida;
   chamadas sem contexto de publicação não podem se converter em bypass
   de campanha. `external_started_at`/resultado incerto continuam
   `unknown`, sem reenvio automático.
5. **Retry manual de campanha fica bloqueado enquanto inerte.** A RPC
   legada `062_manual_post_retry.sql` cria novo UUID e não herda vínculos;
   `UNIQUE(occurrence_id,network)` do SQL proposto não permite simplesmente
   anexar uma segunda tentativa à mesma ocorrência. Antes de desbloquear,
   decidir uma identidade de dispatch separada das tentativas, com
   idempotência e quota explícitas; não alterar migration histórica.
6. Exclusão de conta/perfil/post deve continuar possível conforme
   finalidade, retenção legal e solicitação do titular. FKs `RESTRICT`
   permanentes da proposta B3 podem quebrar cascatas existentes;
   projetar purge autorizado/anonimização e testes de lifecycle antes de
   qualquer aplicação. Não guardar PII indefinidamente para preservar link.
7. Direitos de assinatura são calculados pelo período **efetivamente
   quitado**: pedido de downgrade/cancelamento não pausa durante o ciclo.
   Em `current_period_end` efetivo: Premium→Pro pausa campanhas para escolha
   explícita de até 2 por perfil; →Free pausa todas, preservando histórico.
   O motor de cobrança e vigência **ainda não existe**; não inventar
   campos/integração de billing nesta fase.

## Sequência de rollout e reversão obrigatória

| Gate | Mudança prevista | Condição para avançar |
|---|---|---|
| G0 — agora | Apenas este contrato, status/documentação e revisão independente. Não mudar executores, jobs nem SQL compartilhada. | PR/CI de documentação, decisão técnica explícita. |
| G1 — desenho de migração | Revisar DDL e testes PostgreSQL descartável: origem imutável, constraints/finalização atômica, exclusão, retry bloqueado. Pré-inspecionar cardinalidades e lock/custo dos seis índices. | Plano de DDL revisado e autorização **específica** para banco compartilhado. |
| G2 — schema aditivo | Implantar schema compatível sem campanhas inseridas; construir índices concorrentes onde apropriado e validar FKs em etapas. `CREATE INDEX CONCURRENTLY` não pode estar em `BEGIN`; tratar índice `INVALID` após falha. Nunca aplicar o SQL B3 atual diretamente no boot. | Auditoria de schema, RLS/grants, locks, exclusão e ausência de jobs F4E. |
| G3 — leitores protegidos | Testes com legado + nova origem e implantação de **ambos** os executores (`staging` e `main`), com flags OFF; autorização de promoção à main independente. | Ambos LIVE no SHA compatível, todos os workers antigos drenados, reconciliação e retry sem bypass; teste de rollback. |
| G4 — produtores controlados | Só então ligar criação atômica de intenção F4E ainda sem envio, após validação de mídia privada, OAuth por perfil, quota por rede/dia de São Paulo, T−30, propriedade e `service_role`. | Testes de concorrência, downgrade efetivo e revisão de permissões. |
| G5 — canário externo | Habilitar um destino nomeado e uma conta autorizada; monitorar claim, barreira pré-envio, resultado incerto e rollback sem replay cego. | **Nova autorização expressa**, pós-observabilidade; não inclui este plano. |

**Rollback:** antes de qualquer linha `campaign`, rollback de leitores
compatíveis pode ser considerado com verificação de filas vazias. Após
qualquer intenção F4E, rollback para `main` antiga é **proibido** enquanto
essa versão puder ler a tabela; primeiro bloquear produtores, drenar,
preservar/neutralizar filas e comprovar compatibilidade. Reverter DDL
não é medida automática de emergência.

## Testes de aceite (a executar antes do G2/G3)

- Legado em ambos os ambientes: criação, claim, recover/requeue, retry,
  cancelamento e publicação apenas **mockada** sem regressão.
- Origem `NULL`, inválida ou alterada rejeitada; leitor antigo, ausência
  de link e erro de SQL não classificam campanha como `legacy`.
- Falha em qualquer inserção de pais/link reverte tudo; nenhum scheduler
  ou job executável parcial.
- Campanha inerte recusada no mirror/enqueue/claim/recovery/retry/pré-envio
  mesmo com flags centrais ON; corrida cancelamento × claim/pré-envio falha
  fechada.
- Retry legado idempotente; campanha bloqueada. Envio `unknown` jamais
  recuperado como duplicata automática.
- Exclusão/cascata/anônimização de conta, perfil e post vinculados
  responde conforme contrato e não deixa referências pessoais órfãs.
- Simulação da versão `main` anterior com banco compartilhado; **não**
  habilitar escritor de campanha enquanto ela puder consumir linhas F4E.
- Execução em PostgreSQL **descartável** e mocks; não chamar isso de
  teste de postagem real, de produção ou de faturamento.

## Próxima ação autorizável

Preparar em **outro PR** a migração aditiva revisada, prova em banco
descartável e leitores em modo fail-closed, sem criar campanhas.
Isso depende de concluir G1 e de aprovação pontual para a DDL compartilhada
e, em momento distinto, para a proteção de `main`. Não acrescentar
abstrações de runtime inativas apenas para aparentar progresso.

Referências: [B3](../../F4E-2B3-PROPOSTA-IDENTIDADE-PAIS-20261103.md),
[SQL apenas-proposta](../../sql-proposals/F4E2B2-INERT-CAMPAIGN-DISPATCH-LINKS.sql),
[política de planos](../../PLANOS-F4-POLITICAS-E-FASES-20261103.md),
[TASK](../../TASK.md).
