-- Multi-perfil (continuação da 036): profile_id nas demais tabelas com user_id.
-- Aditiva e idempotente: coluna nullable, FK ON DELETE SET NULL (mesma decisão da
-- 036 -- apagar perfil não apaga dado), índice e backfill pro perfil principal.
-- Constraints UNIQUE existentes NÃO são alteradas aqui (ver 039).
-- RLS/policies block_all_api não são tocadas.

-- shopee_credentials
alter table public.shopee_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_shopee_credentials_profile_id on public.shopee_credentials (profile_id);
update public.shopee_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- threads_credentials
alter table public.threads_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_threads_credentials_profile_id on public.threads_credentials (profile_id);
update public.threads_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- x_credentials
alter table public.x_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_x_credentials_profile_id on public.x_credentials (profile_id);
update public.x_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- facebook_credentials
alter table public.facebook_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_facebook_credentials_profile_id on public.facebook_credentials (profile_id);
update public.facebook_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- instagram_credentials
alter table public.instagram_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_instagram_credentials_profile_id on public.instagram_credentials (profile_id);
update public.instagram_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- tiktok_credentials
alter table public.tiktok_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_tiktok_credentials_profile_id on public.tiktok_credentials (profile_id);
update public.tiktok_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- kwai_credentials
alter table public.kwai_credentials add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_kwai_credentials_profile_id on public.kwai_credentials (profile_id);
update public.kwai_credentials t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- credential_checks
alter table public.credential_checks add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_credential_checks_profile_id on public.credential_checks (profile_id);
update public.credential_checks t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- posts
alter table public.posts add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_posts_profile_id on public.posts (profile_id);
update public.posts t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- medias
alter table public.medias add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_medias_profile_id on public.medias (profile_id);
update public.medias t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- schedulers
alter table public.schedulers add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_schedulers_profile_id on public.schedulers (profile_id);
update public.schedulers t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- activities
alter table public.activities add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_activities_profile_id on public.activities (profile_id);
update public.activities t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- request_logs
alter table public.request_logs add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_request_logs_profile_id on public.request_logs (profile_id);
update public.request_logs t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;

-- audit_events
alter table public.audit_events add column if not exists profile_id uuid references profiles(id) on delete set null;
create index if not exists idx_audit_events_profile_id on public.audit_events (profile_id);
update public.audit_events t
set profile_id = pr.id
from public.profiles pr
where pr.user_id = t.user_id and pr.kind = 'principal' and t.profile_id is null;
