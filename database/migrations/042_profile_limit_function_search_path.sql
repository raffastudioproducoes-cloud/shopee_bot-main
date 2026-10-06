-- Migração 042: Define search_path para enforce_profile_limit()
-- Alerta do Supabase Advisor: function_search_path_mutable
-- Idempotente: verifica se a alteração já existe antes de aplicar

do $$
begin
  -- Somente executa se a função ainda não tiver o search_path configurado
  if not exists (
    select 1
    from pg_proc
    join pg_namespace on pg_proc.pronamespace = pg_namespace.oid
    where pg_namespace.nspname = 'public'
      and pg_proc.proname = 'enforce_profile_limit'
      and pg_proc.prosecdef = false
      and (pg_proc.proconfig @> array['search_path=public, pg_temp']
           or (pg_proc.proconfig is null))
  ) then
    alter function public.enforce_profile_limit() set search_path = public, pg_temp;
  end if;
end $$;
