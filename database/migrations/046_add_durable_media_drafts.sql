begin;

-- Rascunhos não entram em medias: a migration 014 remove linhas sem vínculo
-- em posts_medias e não pode apagar um upload temporário válido.
create table if not exists public.temporary_media_uploads (
    id uuid primary key,
    user_id uuid not null references public.users(id) on delete cascade,
    profile_id uuid not null references public.profiles(id) on delete cascade,
    storage_bucket text not null,
    storage_key text not null unique,
    file_name text not null,
    mime_type text not null,
    size_bytes integer not null check (size_bytes > 0 and size_bytes <= 52428800),
    media_type mediaType not null,
    status text not null default 'uploading'
        check (status in ('uploading', 'ready', 'consumed', 'delete_failed')),
    expires_at timestamptz not null,
    created_at timestamptz not null default now(),
    consumed_at timestamptz
);

create index if not exists idx_temporary_media_owner_expiry
    on public.temporary_media_uploads (user_id, profile_id, status, expires_at);

-- Não há acesso direto do navegador à tabela nem ao bucket. O serviço usa a
-- chave de servidor, que ignora RLS; anon/authenticated não recebem policy.
alter table public.temporary_media_uploads enable row level security;
revoke all on table public.temporary_media_uploads from anon, authenticated;

-- O bucket não é público: a API servidor a servidor é a única leitora e
-- escritora. Nenhuma URL assinada é retornada ao frontend nesta etapa.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'post-media', 'post-media', false, 52428800,
    array['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

commit;
