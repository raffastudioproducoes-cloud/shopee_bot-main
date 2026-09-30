-- Applied to production (Supabase: autovendas) on 2026-09-29 via Supabase MCP

create index if not exists idx_products_user_id on public.products (user_id);
create index if not exists idx_product_lists_user_id on public.product_lists (user_id);
create index if not exists idx_product_lists_products_product_id on public.product_lists_products (product_id);
create index if not exists idx_activities_activity_id on public.activities (activity_id);
create index if not exists idx_activities_user_id on public.activities (user_id);
create index if not exists idx_shopee_credentials_user_id on public.shopee_credentials (user_id);
create index if not exists idx_threads_credentials_user_id on public.threads_credentials (user_id);
create index if not exists idx_posts_post_id on public.posts (post_id);
create index if not exists idx_posts_user_id on public.posts (user_id);
create index if not exists idx_medias_user_id on public.medias (user_id);
create index if not exists idx_posts_medias_media_id on public.posts_medias (media_id);
create index if not exists idx_posts_products_product_id on public.posts_products (product_id);
create index if not exists idx_schedulers_post_id on public.schedulers (post_id);
create index if not exists idx_schedulers_user_id on public.schedulers (user_id);
create index if not exists idx_x_credentials_user_id on public.x_credentials (user_id);
create index if not exists idx_facebook_credentials_user_id on public.facebook_credentials (user_id);
create index if not exists idx_instagram_credentials_user_id on public.instagram_credentials (user_id);
create index if not exists idx_tiktok_credentials_user_id on public.tiktok_credentials (user_id);
create index if not exists idx_kwai_credentials_user_id on public.kwai_credentials (user_id);
