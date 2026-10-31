-- A mesma identidade Threads pode ser autorizada em mais de uma conta do app.
-- A unicidade anterior em t_user_id impedia a conta temporária de revisão
-- de usar o mesmo token do titular, mesmo com autorização explícita.
-- Mantemos unicidade por usuário: dois registros iguais na MESMA conta
-- continuam impedidos; acesso às credenciais segue isolado por user_id
-- na API e bloqueado por RLS para clientes diretos.
--
-- A mudança é de schema apenas: nenhuma credencial ou token é exposto,
-- alterado ou transferido por esta migração.
begin;

alter table public.threads_credentials
    drop constraint if exists threads_credentials_t_user_id_key;

create unique index if not exists uq_threads_credentials_user_t_user_id
    on public.threads_credentials (user_id, t_user_id);

commit;
