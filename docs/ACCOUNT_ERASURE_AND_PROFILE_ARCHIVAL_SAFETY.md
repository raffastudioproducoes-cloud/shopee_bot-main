# Exclusão de perfil e apagamento integral da conta — contrato de segurança (rascunho)

> **NÃO IMPLANTADO.** Plano técnico para PR #266 em `feat/profile-archive-history-20261104`. O banco Supabase é **compartilhado** por staging e main. Nenhuma migração 080 foi aplicada; nenhum perfil, usuário ou arquivo real foi excluído durante esta preparação.

## Decisão canônica (04/11/2026)

1. **Remover perfil secundário:** arquivar a identidade operacional (`profiles.archived_at`), retirar de seleção/lista e de cotas de perfil, cancelar agendamentos/recorrências/campanhas que aguardam despachar. Não apagar posts, atividades, mídia histórica, jobs terminais e registros necessários para conciliação. Perfil principal não pode ser removido isoladamente.
2. **Resultado final:** manter `succeeded`, `failed` e `unknown` (incerteza pós-início de chamada externa, a conciliar; não fingir sucesso nem reenviar). Agendas canceladas devem sair da contagem de despacho ativo; seus `schedulers` podem precisar permanecer como pai de `publish_jobs` terminais pela FK `ON DELETE CASCADE`.
3. **Excluir conta inteira:** depois de autenticação reforçada, apagar **todos** os perfis, inclusive arquivados, e todos os históricos, dados, credenciais, arquivos do Supabase Storage e identidade vinculada em Supabase Auth. A operação não pode ser confundida com excluir um perfil. Não manter auditoria identificável da conta excluída. Nenhum perfil ou conta real será excluído para testar.

## Fatos verificados no banco compartilhado (somente leitura)

- `profiles` ainda **não** possui `archived_at`; o SQL 080 está apenas em `docs/sql-proposals`.
- `publish_jobs.scheduler_id` é NOT NULL e `ON DELETE CASCADE`: remover a agenda apagaria resultados finais. Preservar o pai, cancelar `dispatch_cancelled_at`, barrar claim/preflight.
- Tabelas F4E ligadas a `profiles` usam `ON DELETE CASCADE`, inclusive campanhas/reservas/slots. Delete físico de perfil é proibido.
- `audit_events.user_id` tem `ON DELETE SET NULL`, não CASCADE; `audit_events.entity_id` é texto. `request_logs.user_id` não tem FK para `users`. Delete em `public.users` **não apaga tudo**.
- `users.supabase_auth_user_id` pode apontar para `auth.users`; remover `public.users` sozinho não remove identidade Auth.
- Storage usa buckets `post-media` e `avatars`; existem referências em `medias.file_path`, `temporary_media_uploads.storage_bucket/storage_key`, `campaign_draft_media`, `campaign_reservation_assets_f4e`. Arquivos só podem ser removidos pelo **Supabase Storage API**, não por SQL em `storage.objects`.

## Contrato da implementação integral ainda pendente

A exclusão definitiva da conta requer um **fluxo durável, idempotente e retomável**, sem novo cron:

1. Validar senha/identidade, plano de autorização, escopo de `user_id`, proteção da conta principal da empresa; exigir papel administrativo no endpoint de administração.
2. Em transação com lock da conta, gravar estado `deletion_pending` e registro de progresso durável; bloquear login, escrita, upload, novos dispatches/claims e trocar perfil. Cancelar pendentes de todos os perfis, sem reenviar `unknown`. Terminar ou reconciliar operações externas já iniciadas.
3. Inventariar **somente objetos comprovadamente pertencentes à conta** (dois buckets, referências de todas as tabelas, caminhos por usuário/perfil inclusive perfil arquivado). Não apagar mídia de outro titular. Executar remoção via Storage API, em lotes e com verificação/retry; reconciliar uploads em voo. Persistir o progresso sem informações sensíveis desnecessárias.
4. Excluir identidade vinculada pelo **Auth Admin API** com chave de serviço no backend, nunca no browser. Ausência de identidade já removida deve ser etapa idempotente. Validar revogação das sessões da API.
5. Em transação de DB, excluir explicitamente `request_logs`, `audit_events` vinculados por `user_id`, `profile_id`, `entity_id` e outros dados sem FK; remover `public.users` para cascatas; checar zero órfãos. Considerar auditoria com IDs em JSON e observabilidade externa. Finalizar/limpar registro de progresso somente depois de sucesso verificável.
6. Se qualquer etapa falhar, **não responder sucesso** e manter estado recuperável para continuação segura; nenhum DELETE simples de `public.users` é permitido. Logs de diagnóstico sanitizados. Sem disparar publicação no retry.

A escolha de um registro transacional intermediário é necessária porque operações em PostgreSQL, Storage API e Supabase Auth **não pertencem à mesma transação**. Um `DELETE` com cascata não atende a essa exigência.

## Gates obrigatórios

- [ ] Provisionar PostgreSQL descartável ou instância isolada de staging para migrações, sem DDL no Supabase compartilhado.
- [ ] Testes completos do SQL 080: contas A/B, Free/Pro/Premium, principal, histórico terminal, `unknown`, concorrência `claim/preflight` e cancelamento F4E.
- [ ] Implementar e validar operação idempotente de apagamento integral (Auth + Storage + DB) e recuperação de falha em cada etapa, com dados sintéticos.
- [ ] Auditar todas as rotas que aceitam `profile_id` explícito, quota, refresh, RLS e interface de históricos arquivados.
- [ ] Revisar compatibilidade entre backend de produção antigo e coluna/marcador de arquivamento; preparar rollout `expand → deploy compatível → enable → contract`.
- [ ] CI verde, staging LIVE e homologação do Rafa. **Main somente após aprovação explícita**.

## Estado da branch

O código atual bloqueia exclusão física insegura (`503`) caso o arquivamento não esteja habilitado e também bloqueia o DELETE incompleto de conta (`503`). Os endpoints de leitura continuam operando com schema atual, sem gate. Não aplicar `PROFILE_ARCHIVAL_ENABLED=true` enquanto não existir coluna/RPC e plano de rollout aprovado. Nenhum dado ou scheduler em produção foi modificado.
