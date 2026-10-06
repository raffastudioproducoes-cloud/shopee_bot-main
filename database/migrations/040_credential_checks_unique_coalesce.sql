-- O índice único da 039 trata NULLs como distintos: linhas legadas com
-- profile_id NULL podiam duplicar (user_id, network). Recria o índice com
-- coalesce(profile_id, uuid nulo) para que NULL também seja único.
-- Antes, dedupe de linhas NULL duplicadas mantendo a mais recente. Idempotente.

delete from public.credential_checks c
using public.credential_checks newer
where c.profile_id is null
  and newer.profile_id is null
  and newer.user_id = c.user_id
  and newer.network = c.network
  and (newer.checked_at, newer.id) > (c.checked_at, c.id);

drop index if exists public.uq_credential_checks_user_profile_network;
create unique index if not exists uq_credential_checks_user_profile_network
    on public.credential_checks (user_id, coalesce(profile_id, '00000000-0000-0000-0000-000000000000'::uuid), network);
