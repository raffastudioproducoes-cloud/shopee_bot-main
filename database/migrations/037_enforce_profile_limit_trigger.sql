-- Limite de 3 perfis por conta imposto no banco (atomico).
-- O check "count + insert" do app (POST /profiles) tem race (TOCTOU): duas
-- requisicoes simultaneas passam ambas pelo count. O trigger serializa os
-- inserts do mesmo usuario com advisory lock transacional e recontagem.
-- Idempotente (create or replace / drop trigger if exists) e aditiva.

create or replace function public.enforce_profile_limit()
returns trigger
language plpgsql
as $$
begin
  perform pg_advisory_xact_lock(hashtext(new.user_id::text));
  if (select count(*) from public.profiles where user_id = new.user_id) >= 3 then
    raise exception 'profile_limit_exceeded' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_enforce_profile_limit on public.profiles;
create trigger trg_enforce_profile_limit
  before insert on public.profiles
  for each row execute function public.enforce_profile_limit();
