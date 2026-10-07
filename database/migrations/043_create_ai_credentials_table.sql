-- Chave de IA (Gemini/OpenAI/Anthropic) do PRÓPRIO usuário/perfil, usada
-- pelo "Gerar texto com IA" (POST /posts/generate-copy). Substitui a chave
-- global GEMINI_API_KEY do servidor (sem fallback global).
-- `secret` é cifrado na API (api/crypto.py, Fernet) e nunca devolvido.
-- Aditiva e idempotente: roda sozinha no boot (database.init ->
-- run_migrations) contra o Postgres compartilhado por prod e staging.
create table if not exists public.ai_credentials (
    id serial primary key,
    user_id uuid not null references users(id) on delete cascade,
    profile_id uuid references profiles(id) on delete set null,
    provider text not null check (provider in ('gemini', 'openai', 'anthropic')),
    secret text,
    model text,
    status boolean not null default false,
    created_at timestamp default current_timestamp,
    updated_at timestamp default current_timestamp
);

create unique index if not exists uq_ai_credentials_user_profile_provider
    on public.ai_credentials (user_id, coalesce(profile_id, '00000000-0000-0000-0000-000000000000'::uuid), provider);
create index if not exists idx_ai_credentials_profile_id on public.ai_credentials (profile_id);

alter table public.ai_credentials enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'ai_credentials' and policyname = 'block_all_api'
  ) then
    create policy "block_all_api" on public.ai_credentials for all using (false) with check (false);
  end if;
end $$;
