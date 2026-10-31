-- 059: corrigir grants de tabela ja criada por migracao 058 em 31/10.
-- O Supabase concede por default todos os privilegios a service_role;
-- a aplicacao so precisa executar RPCs SECURITY DEFINER (postgres).
REVOKE ALL ON TABLE public.storage_upload_reservations FROM service_role;
