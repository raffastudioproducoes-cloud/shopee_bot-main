-- Grupo EXATO de um envio multi-rede: o front gera um UUID por submissão e
-- manda o mesmo em cada post criado (um por rede). Substitui a heurística
-- "mesmo texto em < 2 min", que deixou de servir quando cada rede pode ter
-- o seu texto (variantes por limite de caracteres).
-- Aditiva e idempotente: roda sozinha no boot (database.init ->
-- run_migrations) contra o Postgres compartilhado por prod e staging.
-- Nullable, sem default: posts antigos ficam com NULL (a lista cai na
-- heurística antiga só pra eles) e o código atual de produção a ignora.
alter table public.posts add column if not exists group_id uuid;
create index if not exists idx_posts_group_id on public.posts (group_id);
