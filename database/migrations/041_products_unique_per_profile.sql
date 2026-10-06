-- Multi-perfil: o mesmo produto (product_id da Shopee) deve poder existir em
-- 2 perfis da mesma conta. Troca UNIQUE (product_id, user_id) (002) por um
-- índice único por perfil; linhas legadas com profile_id NULL continuam
-- únicas por (user_id, product_id) via coalesce. Nenhum dado é alterado e
-- nenhuma FK referencia a constraint antiga (as tabelas de junção apontam
-- para products.id). Idempotente.

alter table public.products drop constraint if exists products_product_id_user_id_key;

create unique index if not exists uq_products_user_product_profile
    on public.products (user_id, product_id, coalesce(profile_id, '00000000-0000-0000-0000-000000000000'::uuid));
