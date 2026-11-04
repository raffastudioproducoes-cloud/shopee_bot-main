# Exclusão de perfil e apagamento integral da conta — contrato de segurança (rascunho)

> **ESQUEMA APLICADO, FUNCIONALIDADE NÃO ATIVADA.** O Supabase continua **único e compartilhado** entre staging/main, como autorizado pelo Rafa. Migrações 080 (arquivamento), 081 (coordenação do expurgo) e 082 (correção de view) registradas no banco em 04/11/2026. A API está na PR #266, ainda draft, com `PROFILE_ARCHIVAL_ENABLED=false` e `ACCOUNT_ERASURE_ENABLED=false` por padrão. Não foi excluído nenhum perfil, usuário, arquivo ou histórico real.

## Decisão canônica (04/11/2026)

1. **Remover perfil secundário:** arquivar a identidade operacional (`profiles.archived_at`), retirar de seleção/lista e de cotas de perfil, cancelar agendamentos/recorrências/campanhas que aguardam despachar. Não apagar posts, atividades, mídia histórica, jobs terminais e registros necessários para conciliação. Perfil principal não pode ser removido isoladamente.
2. **Resultado final:** manter `succeeded`, `failed` e `unknown` (incerteza pós-início de chamada externa, a conciliar; não fingir sucesso nem reenviar). Agendas canceladas devem sair da contagem de despacho ativo; seus `schedulers` podem precisar permanecer como pai de `publish_jobs` terminais pela FK `ON DELETE CASCADE`.
3. **Excluir conta inteira:** depois de autenticação reforçada, apagar **todos** os perfis, inclusive arquivados, e todos os históricos, dados, credenciais, arquivos do Supabase Storage e identidade vinculada em Supabase Auth. A operação não pode ser confundida com excluir um perfil. Não manter auditoria identificável da conta excluída. Nenhum perfil ou conta real será excluído para testar.

## Fatos verificados e schema autorizado no banco compartilhado

- `profiles.archived_at` e a RPC `archive_profile_with_history` **já existem** após a migração 080. RPC executável somente por `service_role`; `anon` e `authenticated` bloqueados. Nenhum perfil foi arquivado.
- `publish_jobs.scheduler_id` é NOT NULL e `ON DELETE CASCADE`: remover a agenda apagaria resultados finais. Preservar o pai, cancelar `dispatch_cancelled_at`, barrar claim/preflight.
- Tabelas F4E ligadas a `profiles` usam `ON DELETE CASCADE`, inclusive campanhas/reservas/slots. Delete físico de perfil é proibido.
- `audit_events.user_id` tem `ON DELETE SET NULL`, não CASCADE; `audit_events.entity_id` é texto. `request_logs.user_id` não tem FK para `users`. Delete em `public.users` **não apaga tudo**.
- `users.supabase_auth_user_id` pode apontar para `auth.users`; remover `public.users` sozinho não remove identidade Auth.
- Storage usa buckets `post-media` e `avatars`; existem referências em `medias.file_path`, `temporary_media_uploads.storage_bucket/storage_key`, `campaign_draft_media`, `campaign_reservation_assets_f4e`. Arquivos só podem ser removidos pelo **Supabase Storage API**, não por SQL em `storage.objects`.

## Implementação do apagamento integral — branch isolada, feature flag OFF

A branch implementa a coordenação do **fluxo durável, idempotente e retomável**, sem novo cron (`api/account_erasure.py`, migrations 081/082 e rotas protegidas). O deploy e a ativação ainda exigem validação operacional de Storage/Auth. Etapas:

1. Validar senha/identidade (Supabase Auth se houver identidade vinculada, bcrypt legado caso contrário), escopo de `user_id`, proteção da conta principal da empresa; exigir administrador nas operações administrativas e na retomada.
2. Em transação com lock da conta, gravar estado `deletion_pending` e registro de progresso durável; bloquear login, escrita, upload, novos dispatches/claims e trocar perfil. Cancelar pendentes de todos os perfis, sem reenviar `unknown`. Terminar ou reconciliar operações externas já iniciadas.
3. Inventariar **somente objetos comprovadamente pertencentes à conta** (dois buckets, referências de todas as tabelas, caminhos por usuário/perfil inclusive perfil arquivado). Não apagar mídia de outro titular. Executar remoção via Storage API, em lotes e com verificação/retry; reconciliar uploads em voo. Persistir o progresso sem informações sensíveis desnecessárias.
4. Excluir identidade vinculada pelo **Auth Admin API** com chave de serviço no backend, nunca no browser. Ausência de identidade já removida deve ser etapa idempotente. Validar revogação das sessões da API.
5. Em transação de DB, excluir explicitamente `request_logs`, `audit_events` vinculados por `user_id`, `profile_id`, `entity_id`/IDs de recursos e `post_content_revisions` sem FK de usuário; também remove `request_logs` identificados somente pelo username da conta (083); remover `public.users` para cascatas; checar zero órfãos. A `campaign_progress_f4e` é uma **view**, nunca receber DELETE (correção 082). Finalizar/limpar registro de progresso somente depois de sucesso verificável.
6. Se qualquer etapa falhar, **não responder sucesso** e manter estado recuperável para continuação segura; nenhum DELETE simples de `public.users` é permitido. Logs de diagnóstico sanitizados. Sem disparar publicação no retry.

A escolha de um registro transacional intermediário é necessária porque operações em PostgreSQL, Storage API e Supabase Auth **não pertencem à mesma transação**. Um `DELETE` com cascata não atende a essa exigência.

## Gates obrigatórios

- [x] Rafa autorizou migrações aditivas no Supabase compartilhado, sem novo ambiente. Migrações 080/081/082/083/084 aplicadas e permissões SQL conferidas.
- [x] Testes SQL transacionais com conta sintética e `ROLLBACK`: arquivamento, impossibilidade de arquivar principal, idempotência e expurgo DB/audit/request_logs. Contagens originais intactas e zero registros de teste residuais.
- [ ] Testes completos de duas contas, Free/Pro/Premium, histórico F4E/unknown, concorrência `claim/preflight` e mídia real.
- [x] Orquestrador de apagamento Storage API → Auth Admin API → finalizador DB com estado retomável e endpoint admin de recuperação, ainda somente na branch.
- [ ] Testar integração Storage/Auth em staging com identidade e objetos sintéticos próprios (sem excluir dados existentes), validar falhas parciais e recuperação.
- [ ] Auditar todas as rotas que aceitam `profile_id` explícito, quota, refresh, RLS, histórico de arquivos arquivados e tentativas de upload em voo.
- [ ] Revisar compatibilidade entre backend de produção antigo e coluna/marcador de arquivamento; preparar rollout `expand → deploy compatível → enable → contract`.
- [ ] CI da PR atual verde, staging LIVE e homologação do Rafa. **Main somente após aprovação explícita**.

## Evidência e rollout

- Banco compartilhado: migrações 080/081/082/083/084 aplicadas; verificação confirmou 4 perfis, 3 agendas, 3 publish_jobs e 5 objetos Storage antes e depois; zero contas sintéticas e zero tarefas de apagamento pendentes. Um teste SQL de finalização encontrou uma view não deletável e foi corrigido em 082 antes da execução sintética bem-sucedida.
- Nenhum cron, pg_net, worker, agendamento ou serviço foi desligado ou alterado. Nenhum dado real foi excluído.
- Branch `feat/profile-archive-history-20261104` / PR #266 draft. `PROFILE_ARCHIVAL_ENABLED=false` e `ACCOUNT_ERASURE_ENABLED=false` por padrão no código; ativação **não autorizada no main**.
- Staging primeiro, CI e smoke test; main apenas após aceite explícito. O código antigo em produção ainda não filtra `archived_at`; não começar exclusões reais de perfil/conta enquanto os dois ambientes não forem compatíveis.

### Adendo — integridade dos logs (084)

A tabela `request_logs` continha 1.299 linhas antigas cujo `user_id` já não existe em `public.users`. A FK `request_logs_user_id_erasure_fk` foi criada como `NOT VALID` (novas inserções ficam protegidas; nenhum histórico antigo é apagado), com índice `idx_request_logs_user_id_fk`. Teste `BEGIN/ROLLBACK` confirmou `ON DELETE CASCADE` e rejeição de novos logs órfãos. O middleware evita a gravação da própria requisição de exclusão depois do expurgo. Limpeza de logs antigos sem proprietário exige auditoria separada; não foi realizada.
