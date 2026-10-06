create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  kind text not null check (kind in ('principal', 'secundario')),
  plan_tier text not null default 'free' check (plan_tier in ('free', 'plus', 'premium')),
  nome text not null,
  email text,
  telefone text,
  endereco text,
  avatar_url text,
  created_at timestamp not null default current_timestamp,
  updated_at timestamp not null default current_timestamp
);

create index if not exists idx_profiles_user_id on public.profiles (user_id);

alter table public.profiles enable row level security;
create policy "block_all_api" on public.profiles for all using (false) with check (false);

-- Backfill: cada usuario existente ganha 1 perfil principal automaticamente.
insert into public.profiles (user_id, kind, nome)
select id, 'principal', username
from public.users
where not exists (
  select 1 from public.profiles p where p.user_id = users.id and p.kind = 'principal'
);
