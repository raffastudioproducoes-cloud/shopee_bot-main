-- Multi-perfil: dois perfis da mesma conta precisam poder guardar a mesma
-- API Key da Shopee (spec 2.3, pedido explícito de Rafa) e ter um resultado
-- de "Testar conexão" por perfil/rede. Só remove/substitui unicidade; nenhum
-- dado é alterado. Idempotente.

-- shopee_credentials.app_id deixa de ser UNIQUE (nome padrão do Postgres para
-- a coluna declarada com UNIQUE inline na migração 010).
alter table public.shopee_credentials drop constraint if exists shopee_credentials_app_id_key;

-- credential_checks: de UNIQUE (user_id, network) para um check por perfil.
-- Linhas legadas com profile_id NULL continuam permitidas (NULLs são distintos).
alter table public.credential_checks drop constraint if exists credential_checks_user_id_network_key;
create unique index if not exists uq_credential_checks_user_profile_network
    on public.credential_checks (user_id, profile_id, network);
