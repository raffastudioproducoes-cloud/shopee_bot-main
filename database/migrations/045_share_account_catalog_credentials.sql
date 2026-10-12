begin;

-- Conta compartilhada: produtos e credenciais Shopee/IA deixam de pertencer
-- ao perfil ativo. Linhas divergentes abortam antes de qualquer alteracao de
-- dados; mensagens de erro nao incluem valores de credenciais.

lock table public.products, public.product_lists_products, public.posts_products,
    public.shopee_credentials, public.ai_credentials in access exclusive mode;

do $$
begin
    if exists (
        select 1
        from public.products product
        join public.products other
          on other.user_id = product.user_id
         and other.product_id = product.product_id
         and other.id > product.id
        where row(
            product.name, product.original_link, product.commission_link,
            product.commission, product.image, product.price_min, product.price_max
        ) is distinct from row(
            other.name, other.original_link, other.commission_link,
            other.commission, other.image, other.price_min, other.price_max
        )
    ) then
        raise exception 'migration 045 blocked: conflicting account-owned products';
    end if;

    if exists (
        select 1
        from public.shopee_credentials credential
        join public.shopee_credentials other
          on other.user_id = credential.user_id
         and other.id > credential.id
        where row(credential.app_id, credential.secret, credential.status)
            is distinct from row(other.app_id, other.secret, other.status)
    ) then
        raise exception 'migration 045 blocked: conflicting account-owned shopee credentials';
    end if;

    if exists (
        select 1
        from public.ai_credentials credential
        join public.ai_credentials other
          on other.user_id = credential.user_id
         and other.provider = credential.provider
         and other.id > credential.id
        where row(credential.secret, credential.model, credential.status)
            is distinct from row(other.secret, other.model, other.status)
    ) then
        raise exception 'migration 045 blocked: conflicting account-owned ai credentials';
    end if;
end $$;

drop index if exists public.uq_products_user_product_profile;
drop index if exists public.uq_ai_credentials_user_profile_provider;

-- Keep the oldest compatible product and preserve every list/post reference.
with product_duplicates as (
    select id, min(id) over (partition by user_id, product_id) as canonical_id
    from public.products
)
update public.product_lists_products list_product
set product_id = duplicate.canonical_id
from product_duplicates duplicate
where list_product.product_id = duplicate.id
  and duplicate.id <> duplicate.canonical_id
  and not exists (
      select 1
      from public.product_lists_products canonical
      where canonical.product_list_id = list_product.product_list_id
        and canonical.product_id = duplicate.canonical_id
  );

with product_duplicates as (
    select id, min(id) over (partition by user_id, product_id) as canonical_id
    from public.products
)
update public.posts_products post_product
set product_id = duplicate.canonical_id
from product_duplicates duplicate
where post_product.product_id = duplicate.id
  and duplicate.id <> duplicate.canonical_id
  and not exists (
      select 1
      from public.posts_products canonical
      where canonical.post_id = post_product.post_id
        and canonical.product_id = duplicate.canonical_id
  );

with product_duplicates as (
    select id, min(id) over (partition by user_id, product_id) as canonical_id
    from public.products
)
delete from public.products product
using product_duplicates duplicate
where product.id = duplicate.id
  and duplicate.id <> duplicate.canonical_id;

with credential_duplicates as (
    select id, min(id) over (partition by user_id) as canonical_id
    from public.shopee_credentials
)
delete from public.shopee_credentials credential
using credential_duplicates duplicate
where credential.id = duplicate.id
  and duplicate.id <> duplicate.canonical_id;

with credential_duplicates as (
    select id, min(id) over (partition by user_id, provider) as canonical_id
    from public.ai_credentials
)
delete from public.ai_credentials credential
using credential_duplicates duplicate
where credential.id = duplicate.id
  and duplicate.id <> duplicate.canonical_id;

update public.products
set profile_id = null
where profile_id is not null;

update public.shopee_credentials
set profile_id = null
where profile_id is not null;

update public.ai_credentials
set profile_id = null
where profile_id is not null;

create unique index if not exists uq_products_user_product
    on public.products (user_id, product_id);
create unique index if not exists uq_shopee_credentials_user
    on public.shopee_credentials (user_id);
create unique index if not exists uq_ai_credentials_user_provider
    on public.ai_credentials (user_id, provider);

create index if not exists idx_products_user_id on public.products (user_id);
create index if not exists idx_shopee_credentials_user_id
    on public.shopee_credentials (user_id);
create index if not exists idx_ai_credentials_user_id on public.ai_credentials (user_id);

commit;
