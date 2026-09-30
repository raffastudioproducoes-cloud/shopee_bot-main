-- Add profile_id column to products and product_lists tables
-- Links products and lists to their owning profile (principal only)
-- Uses "on delete set null" to preserve data if a profile is deleted

alter table public.products add column if not exists profile_id uuid references profiles(id) on delete set null;
alter table public.product_lists add column if not exists profile_id uuid references profiles(id) on delete set null;

create index if not exists idx_products_profile_id on public.products (profile_id);
create index if not exists idx_product_lists_profile_id on public.product_lists (profile_id);

-- Backfill: Link each product to the principal profile of its user
update public.products p
set profile_id = pr.id
from public.profiles pr
where pr.user_id = p.user_id and pr.kind = 'principal' and p.profile_id is null;

-- Backfill: Link each product_list to the principal profile of its user
update public.product_lists pl
set profile_id = pr.id
from public.profiles pr
where pr.user_id = pl.user_id and pr.kind = 'principal' and pl.profile_id is null;
